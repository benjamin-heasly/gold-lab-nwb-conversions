from typing import Any, Self
from dataclasses import dataclass
import numpy as np

from pyramid.model import InteropData


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

    def get_times_of(self, event_value: float, value_index: int = 0) -> np.ndarray:
        """Get times of any events matching the given event_value.

        By default this searches the first value per event.
        Pass in value_index>0 to use a different value per event.
        """
        value_column = value_index + 1
        matching_rows = (self.event_data[:, value_column] == event_value)
        return self.event_data[matching_rows, 0]

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

    def copy_time_range(self, start_time: float, end_time: float) -> None:
        """Make a new list containing only events with times in half open interval [start_time, end_time).

        This returns a new NumericEventList with a copy of events in the requested range.
        """
        rows_in_range = (self.event_data[:, 0] >= start_time) & (self.event_data[:, 0] < end_time)
        range_event_data = self.event_data[rows_in_range, :]
        return NumericEventList(range_event_data)


class NumericEventReader():
    """Interface for reading event lists from input sources like streaming connections or data files.

    Encapsulate system and library resources for reading from a source.
    Be able to increment through that source and return a list of numeric corresponding to each increment.
    Only one increment should be buffered at a time -- so sockets and large files can be streamed.
    The choice of increment is up to the implementation -- file chunks, data blocks, socket polls -- all fine.
    """

    def read_next(self, timeout: float) -> NumericEventList:
        """Buffer the next increment from the source and convert to numeric events, if any.

        Return a NumericEventList with all events from the increment, or None if no new events before timeout.
        """
        pass  # pragma: no cover


class NumericEventSource():
    """Manage a NumericEventReader and maintain a buffer of events within a finite time range."""

    def __init__(self, reader: NumericEventReader, reader_timeout: float = 1.0, values_per_event: int = 1) -> None:
        self.reader = reader
        self.reader_timeout = reader_timeout
        self.event_list = NumericEventList(np.empty([0, values_per_event + 1]))

    def start_time(self, default: float = 0.0) -> float:
        """The time of the earliest event currently in the buffer, or the default when empty."""
        self.event_list.get_times().min(default)

    def end_time(self, default: float = 0.0) -> float:
        """The time of the last event currently in the buffer, or the default when empty."""
        self.event_list.get_times().max(default)

    def read_until_time(self, goal_time: float, max_empty_reads: int = 2) -> bool:
        """Keep adding events from the reader until reaching a goal time or exhausting retries.

        We might call this once per trial, for each event source: "catch up to the end time of the current trial."

        Sometimes this is easy -- like if we're reading a file we can consume events until we start seeing event
        times that are at or beyond the goal time.  Then we know we've read far enough and we're good for now.

        Sometimes this is less obvious -- like if we're polling a socket for live events.  If a poll returns
        nothing, does that mean we're all caught up or that there's a relevant trial event still on its way
        through the network?  In this case we want to make a best effort to wait, but not wait forever.

        So, we have two exit conditions indicated by return value:
         - return True: We read a new event with time at or beyond the goal time -- we're all caught up.
         - return False: We exhausted our max number of empty reads, each including the reader's timeout -- we 
                         made a good effort to get caught up, but we can't be sure. 
        """
        empty_reads = 0
        while self.end_time() < goal_time and empty_reads < max_empty_reads:
            new_events = self.reader.read_next(timeout=self.reader_timeout)
            if new_events.event_count():
                self.event_list.append(new_events)
            else:
                empty_reads += 1
        return self.end_time() >= goal_time

    def check_for_value(self, event_value: float) -> bool:
        """Read new events from the reader and report when a desired event_value arrives.

        We might call this periodically on a chosen event source while waiting for the next trial.
        This should not block because it would be interleaved with eg GUI updates.

        Returns whether or not the desired event_value arrived.
        """
        new_events = self.reader.read_next(timeout=self.reader_timeout)
        if new_events.event_count():
            self.event_list.append(new_events)
            return new_events.get_times_of(event_value).size > 0
        else:
            return False

    def discard_before(self, start_time: float) -> None:
        """Discard buffered events strictly before the given start_time.
        
        We might call this after we're done extracting a trial.
        This allows the event source to limit memory usage to a relevant time range.
        """
        self.event_list.discard_before(start_time)
