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

    def append_events(self, other: Self) -> None:
        """Add new events at the end of the existing list."""
        self.event_data = np.concatenate([self.event_data, other.event_data])

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

    def shift_times(self, shift: float) -> None:
        """Shift all event times by a constant.

        This modifies the event_data in place.
        """
        self.event_data[:, 0] += shift

    def filter_times(self, start_time: float, end_time: float) -> None:
        """Remove events with times ouside the range [min, max) (half open interval).

        This replaces the event_data with a filtered version.
        """
        rows_in_range = (self.event_data[:, 0] >= start_time) & (self.event_data[:, 0] < end_time)
        self.event_data = self.event_data[rows_in_range, :]

    def get_values(self, value_index: int = 0) -> np.ndarray:
        """Get just the event values, ignoring event times.

        By default this gets only the first value per event.
        Pass in value_index>0 to get a different value.
        """
        return self.event_data[:, 1 + value_index]

    def apply_offset_then_gain(self, offset: float = 0, gain: float = 1) -> None:
        """Transform all event data by a constant gain and offset.

        By convention: apply offset first, then gain.
        This makes it convenient subtract a baseline from eg ecodes, then scale to a fixed precision.

        This modifies the event_data in place.        
        """
        self.event_data[:, 1:] += offset
        self.event_data[:, 1:] *= gain

    def filter_min_and_max(self, min: float, max: float, value_index: int = 0) -> None:
        """Remove events with values ouside the range [min, max) (half open interval).

        By default this applies only to the first value per event.
        Pass in value_index>0 to use a different value.
        This replaces the event_data with a filtered version.
        """
        filter_column = value_index + 1
        rows_in_range = (self.event_data[:, filter_column] >= min) & (self.event_data[:, filter_column] < max)
        self.event_data = self.event_data[rows_in_range, :]


class NumericEventReader():
    """Interface for reading event lists from input sources like streaming connections or data files.

    Encapsulate system and library resources for reading from a source.
    Be able to increment through that source and return a list of numeric corresponding to each increment.
    Only one increment should be buffered at a time -- so sockets and large files can be streamed.
    The choice of increment is up to the implementation -- file chunks, data blocks, socket polls -- all fine.
    """

    def read_next(self) -> NumericEventList:
        """Buffer the next increment from the source and convert to numeric events, if any
        
        Return a NumericEventList containing all events from the increment, or None if no new events.
        """
        pass # pragma: no cover


class NumericEventSource():
    """Manage a NumericEventReader and buffer events within a finite time range."""
    # I have a reader
    # I have a numeric event list that changes over time as a sliding window:
    #  - grows at the end when I ask the reader for next
    #  - shrinks from the beginning when someone asks me to bump my start_time ahead in time 
    # I can ask the reader to keep reading next, until some event time shows up, or I time out
    # I can ask the reader to keep reading next, until some event value shows up, or I time out
    # people can query me for events in the current loaded time range
