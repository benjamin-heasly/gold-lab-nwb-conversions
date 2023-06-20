from typing import Any, Self
from dataclasses import dataclass
import numpy as np

from pyramid.model.model import InteropData


@dataclass
class NumericEventList(InteropData):
    """Wrap a 2D array listing one event per row: [timestamp, value [, value ...]]."""

    event_data: np.ndarray
    """2D array backing the event list.

    event_data must have shape (n, m>=2) where:
     - n is the number of events (one event per row)
     - m is at least 2 (timestamps and values in columns):
       - column 0 holds the event timestamps
       - columns 1+ hold one or more values per event
    """

    def __eq__(self, other: object) -> bool:
        """Compare event_data arrays as-a-whole instead of element-wise."""
        if isinstance(other, self.__class__):
            return np.array_equal(self.event_data, other.event_data)
        else:
            return False

    def to_interop(self) -> Any:
        return self.event_data.tolist()

    @classmethod
    def from_interop(cls, interop) -> Self:
        event_data = np.array(interop)
        return cls(event_data)

    def event_count(self) -> int:
        """Get the number of events in the list.

        Event timestamps are in event_data[:,0].
        So, the number of events is event_data.shape[0].
        """
        return self.event_data.shape[0]

    def values_per_event(self) -> int:
        """Get the number of values per event.

        Event values are in event_data[:,1].
        Optional additional event values may be in event_data[:,2], event_data[:,3], etc.
        So, the number of values per event is (event_data.shape[1] - 1).
        """
        return self.event_data.shape[1] - 1

    def get_times(self) -> np.ndarray:
        """Get just the event times, ignoring event values."""
        return self.event_data[:, 0]

    def get_values(self, value_index: int = 0) -> np.ndarray:
        """Get just the event values, ignoring event times.

        By default this gets only the first value per event.
        Pass in value_index>0 to get a different value.
        """
        return self.event_data[:, 1 + value_index]

    def get_times_of(
        self,
        event_value: float,
        value_index: int = 0,
        start_time: float = None,
        end_time: float = None
    ) -> np.ndarray:
        """Get times of any events matching the given event_value.

        By default this searches the first value per event.
        Pass in value_index>0 to use a different value per event.

        By default this searches all events in the list.
        Pass in start_time restrict to events at or after start_time.
        Pass in end_time restrict to events strictly before end_time.
        """
        if start_time:
            tail_selector = self.event_data[:, 0] >= start_time
        else:
            tail_selector = True

        if end_time:
            head_selector = self.event_data[:, 0] < end_time
        else:
            head_selector = True

        rows_in_range = tail_selector & head_selector

        value_column = value_index + 1
        matching_rows = (self.event_data[:, value_column] == event_value)
        return self.event_data[rows_in_range & matching_rows, 0]

    def append(self, other: Self) -> None:
        """Add new events at the end of the existing list.

        This modifies the event_data in place.
        """
        self.event_data = np.concatenate([self.event_data, other.event_data])

    def discard_before(self, start_time: float) -> None:
        """Discard events that have times strictly less than the given start_time.

        This modifies the event_data in place.
        """
        rows_to_keep = self.event_data[:, 0] >= start_time
        self.event_data = self.event_data[rows_to_keep, :]

    def shift_times(self, shift: float) -> None:
        """Shift all event times by a constant.

        This modifies the event_data in place.
        """
        self.event_data[:, 0] += shift

    def apply_offset_then_gain(self, offset: float = 0, gain: float = 1, value_index: int = 0) -> None:
        """Transform all event data by a constant gain and offset.

        Uses a convention of applying offset first, then gain.
        This comes from ecodes where we might want to subtract an arbitrary baseline then scale to a fixed precision.

        By default this modifies the first value per event.
        Pass in value_index>0 to use a different value per event.

        This modifies the event_data in place.        
        """
        value_column = value_index + 1
        self.event_data[:, value_column] += offset
        self.event_data[:, value_column] *= gain

    def copy_value_range(self, min: float, max: float, value_index: int = 0) -> None:
        """Make a new list containing only events with values in half open interval [min, max).

        By default min and max apply to the first value per event.
        Pass in value_index>0 to use a different value per event.

        This returns a new NumericEventList with a copy of events in the requested range.
        """
        value_column = value_index + 1
        rows_in_range = (self.event_data[:, value_column] >= min) & (self.event_data[:, value_column] < max)
        range_event_data = self.event_data[rows_in_range, :]
        return NumericEventList(range_event_data)

    def copy_time_range(self, start_time: float = None, end_time: float = None) -> None:
        """Make a new list containing only events with times in half open interval [start_time, end_time).

        Omit start_time to copy all events strictly before end_time.
        Omit end_time to copy all events at and after start_time.

        This returns a new NumericEventList with a copy of events in the requested range.
        """
        if start_time:
            tail_selector = self.event_data[:, 0] >= start_time
        else:
            tail_selector = True

        if end_time:
            head_selector = self.event_data[:, 0] < end_time
        else:
            head_selector = True

        rows_in_range = tail_selector & head_selector
        range_event_data = self.event_data[rows_in_range, :]
        return NumericEventList(range_event_data)


class NumericEventReader():
    """Interface for reading numeric event lists from input sources like streaming connections or data files.

    Encapsulate system and library resources for reading from a source.
    Be able to increment through that source and return a list of numeric corresponding to each increment.
    Only one increment should be buffered at a time -- so sockets and large files can be streamed.
    The choice of increment is up to the implementation -- file chunks, data blocks, socket polls -- all fine.

    Implementations should conform Python's "context management protocol" with __enter__() and __exit__().
    That way readers can set up and cleaned up concisely with code like this:

        with MyReader(a_thing) as reader:
            # do things
            reader.read_next()
            # do more things
        # Reader is automatically cleaned up when the "with" exits.
    See: https://peps.python.org/pep-0343/#standard-terminology
    """

    def __enter__(self) -> Any:
        """Return an object we can read_next() on."""
        pass  # pragma: no cover

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Release any resources acquired during __init__() or __enter()__."""
        pass  # pragma: no cover

    def read_next(self, timeout: float) -> NumericEventList:
        """Buffer the next increment from the source and convert to numeric events, if any.

        Return a NumericEventList with all events from the increment, or None if no new events before timeout.
        """
        pass  # pragma: no cover


class NumericEventSource():
    """Manage a NumericEventReader and maintain a buffer of events within a finite time range."""

    # TODO: default min and max to filter on?
    # TOOD: default offset and gain to apply?

    def __init__(
        self,
        reader: NumericEventReader,
        reader_timeout: float = 1.0,
        max_empty_reads: int = 2,
        values_per_event: int = 1,
    ) -> None:
        self.reader = reader
        self.reader_timeout = reader_timeout
        self.max_empty_reads = max_empty_reads
        self.event_list = NumericEventList(np.empty([0, values_per_event + 1]))

    def start_time(self, default: float = 0.0) -> float:
        """The time of the earliest event currently in the buffer, or the default when empty."""
        times = self.event_list.get_times()
        if times.size > 0:
            return times.min()
        else:
            return default

    def end_time(self, default: float = 0.0) -> float:
        """The time of the last event currently in the buffer, or the default when empty."""
        times = self.event_list.get_times()
        if times.size > 0:
            return times.max()
        else:
            return default

    def discard_before(self, start_time: float) -> None:
        """Discard buffered events that have times strictly less than the given start_time.
        """
        self.event_list.discard_before(start_time)

    def read_next(self) -> NumericEventList:
        """Read one increment from the reader and append any new events.

        Return the list of new events added, if any, or else None.
        """
        new_events = self.reader.read_next(timeout=self.reader_timeout)
        if new_events and new_events.event_count():
            self.event_list.append(new_events)
            return new_events
        else:
            return None

    def read_until_time(self, goal_time: float) -> bool:
        """Keep adding events from the reader until reaching a goal time or exhausting max empty reads.

        We might call this once per trial on each event source: "catch up to the end time of the current trial."

        Sometimes this is easy -- like if we're reading a file we can read in events until we start seeing event
        times that are at or beyond the goal time.  Then we know we've read far enough and we're good for now.
        This assumes events come in order.

        Sometimes this is less obvious -- like if we're polling a socket for live events.  If a poll returns
        nothing, does that mean we're all caught up or that there's a relevant trial event still on its way
        to us through the network?  In this case we want to make a best effort to wait, but not wait forever.

        So, we have two exit conditions indicated by return value:
         - return True: We have an event with time at or beyond the goal time -- so are all caught up.
                        Once this returns True and we're caught up to a give goal time, this is idempotent (save to call again).
         - return False: We exhausted our max number of empty reads (each of these including the reader's own timeout).
                         So, we made a good effort to get caught up, but we can't quite be sure. 
        """
        empty_reads = 0
        while self.end_time() < goal_time and empty_reads < self.max_empty_reads:
            new_events = self.read_next()
            if not new_events or not new_events.event_count():
                empty_reads += 1
        return self.end_time() >= goal_time
