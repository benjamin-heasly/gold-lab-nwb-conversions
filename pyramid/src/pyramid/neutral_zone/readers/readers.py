from typing import Any
from dataclasses import dataclass
import logging

from pyramid.model.numeric_events import NumericEventList, NumericEventBuffer


class Reader():
    """Interface for consuming data from arbitrary sources and converting to Pyramid data model types.

    Each reader implementation should:
     - Encapsulate the details of how to connect to a data source and get data from it.
     - Maintain internal state related to the data source, like a file handle and cursor, data block index,
       socket descriptor, etc.
     - Implement read_next() to consume an increment of available data from the source, update internal state
       to reflect this, and return results in the form of named Pyramid data model types.
     - Implement __enter__() and __exit__() to confirm to Python's "context manager protocol"", which
       is how Pyramid manages acquisition and release of system and libarary resources.
       See: https://peps.python.org/pep-0343/#standard-terminology

    Pyramid takes the results of read_next() from each reader and handles how the results are copied into
    connected buffers, filtered and transformed into desired forms, and eventually assigned to trials.
    So, the focus of a reader implementation can just be getting data out of the source incrementally
    and converting each increment into Pyramid data model types, like NumericEventList.
    """

    def __enter__(self) -> Any:
        """Connect to a data source and acquire related system or library resources.

        Return an object that we can "read_next()" on -- probably just "return self".
        """
        raise NotImplementedError

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Release any resources acquired during __enter()__."""
        raise NotImplementedError

    def read_next(self) -> dict[str, NumericEventList]:
        """Read/poll for new data at the connected source and convert available data to Pyramid types.

        This must not block when reading from its data source.
        Rather, it should read/poll for data once and just return None if no data are available yet.
        Pyramid will call read_next() again, soon, to catch data when it is available.
        This convention allows multiple concurrent readers to be interleaved,
        and for the readers to be interleaved with other tasks like interactive GUI user event handling.

        The implementation can choose its own read/poll strategy or timeout.
        Returning from read_next() within 1-5 milliseconds should be good.

        Return a dicitonary of any data consumed during the read increment, or None if no data available.
        Dictionary values must all be Pyramid data model types like NumericEventList.
        Dictionary keys should suggest an interpretation of the interpretation, like "spikes", "event_codes", etc.
        """
        raise NotImplementedError


class Transformer():
    """Transform values and/or type of Pyramid data, like NumericEventList."""

    def transform(data: NumericEventList) -> NumericEventList:
        return data


@dataclass
class ReaderRoute():
    """Specify the mapping from a reader result entry to a named buffer."""

    reader_name: str
    """How the reader referred a result, like "spikes", "events", etc."""

    buffer_name: str
    """Name for the buffer that will receive reader results "spikes", "ecodes", etc."""

    transformers: list[Transformer] = None
    """Optional data transformations between reader and buffer.

    I think we can add per-event transformations here, like:
     - linear transform with offset and gain 
     - filtering with min and max
     - split event values into multiple events or multiple values-per-event

    We're also interested in per-trial transformations but these might have to wait
    until we have each whole trial delimited and all the related events in one list.
     - rummage around within a trial for related events
     - join related values into complex events or other types, like strings
    """


class ReaderRouter():
    """Get incremental results from a reader, copy and route the data into named buffers.

    If the reader throws an exception, it will be ignored going forward.
    This would apply to error situations as well as orderly end-of-data situations.
    """

    def __init__(
        self,
        reader: Reader,
        buffers: dict[str, NumericEventBuffer],
        routes: list[ReaderRoute],
        empty_reads_allowed: int = 3
    ) -> None:
        self.reader = reader
        self.buffers = buffers
        self.routes = routes

        self.reader_exception = None
        self.max_buffer_time = 0.0
        self.empty_reads_allowed = empty_reads_allowed

    def still_going(self) -> bool:
        return not self.reader_exception

    def route_next(self) -> bool:
        if self.reader_exception:
            return False

        try:
            result = self.reader.read_next()
        except Exception as exception:
            self.reader_exception = exception
            logging.warning("Reader had an exception and will be ignored going forward:", exc_info=True)
            return False

        if not result:
            return False

        for route in self.routes:
            buffer = self.buffers.get(route.buffer_name, None)
            if not buffer:
                continue

            data = result.get(route.reader_name, None).copy()
            if not data:
                continue

            if route.transformers:
                try:
                    for transformer in route.transformers:
                        data = transformer.transform(data)
                except Exception as exception:
                    logging.error("Route transformer had an exception:", exc_info=True)
                    continue

            buffer.append(data)

        # Update the high water mark for the reader -- the latest timestamp seen so far.
        buffer_end_times = [buffer.end_time() for buffer in self.buffers.values()]
        self.max_buffer_time = max(buffer_end_times)

        return True

    def route_until(self, target_time: float) -> float:
        empty_reads = 0
        while self.max_buffer_time < target_time and empty_reads < self.empty_reads_allowed:
            got_data = self.route_next()
            if not got_data:
                empty_reads +=1

        return self.max_buffer_time
