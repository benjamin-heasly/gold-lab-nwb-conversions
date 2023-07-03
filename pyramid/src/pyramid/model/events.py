from typing import Any, Self
from dataclasses import dataclass
import numpy as np

from pyramid.model.model import BufferData


@dataclass
class NumericEventList(BufferData):
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
            return (self.event_data.size == 0 and other.event_data.size == 0) or np.array_equal(self.event_data, other.event_data)
        else:
            return False    

    def copy(self) -> Self:
        """Implementing BufferData superclass."""
        return NumericEventList(self.event_data.copy())

    def copy_time_range(self, start_time: float = None, end_time: float = None) -> Self:
        """Implementing BufferData superclass."""
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

    def append(self, other: Self) -> None:
        """Implementing BufferData superclass."""
        self.event_data = np.concatenate([self.event_data, other.event_data])

    def discard_before(self, start_time: float) -> None:
        """Implementing BufferData superclass."""
        rows_to_keep = self.event_data[:, 0] >= start_time
        self.event_data = self.event_data[rows_to_keep, :]

    def shift_times(self, shift: float) -> None:
        """Implementing BufferData superclass."""
        if self.event_data.size > 0:
            self.event_data[:, 0] += shift

    def get_start_time(self) -> float:
        """Implementing BufferData superclass."""
        if self.event_count():
            return self.event_data[:, 0].min()
        else:
            return None

    def get_end_time(self) -> float:
        """Implementing BufferData superclass."""
        if self.event_count():
            return self.event_data[:, 0].max()
        else:
            return None

    def to_interop(self) -> Any:
        """Implementing InteropData superclass."""
        return self.event_data.tolist()

    @classmethod
    def from_interop(cls, interop) -> Self:
        """Implementing InteropData superclass."""
        event_data = np.array(interop)
        return cls(event_data)

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

    def apply_offset_then_gain(self, offset: float = 0, gain: float = 1, value_index: int = 0) -> None:
        """Transform all event data by a constant gain and offset.

        Uses a convention of applying offset first, then gain.
        This comes from ecodes where we might want to subtract an arbitrary baseline then scale to a fixed precision.

        By default this modifies the first value per event.
        Pass in value_index>0 to use a different value per event.

        This modifies the event_data of this object, in place.
        """
        value_column = value_index + 1
        self.event_data[:, value_column] += offset
        self.event_data[:, value_column] *= gain

    def get_times(self) -> np.ndarray:
        """Get just the event times, ignoring event values."""
        return self.event_data[:, 0]

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

    def get_values(self, value_index: int = 0) -> np.ndarray:
        """Get just the event values, ignoring event times.

        By default this gets only the first value per event.
        Pass in value_index>0 to get a different value.
        """
        return self.event_data[:, 1 + value_index]

    def copy_value_range(self, min: float = None, max: float = None, value_index: int = 0) -> Self:
        """Make a new list containing only events with values in half open interval [min, max).

        Omit min to copy all events with value strictly less than max.
        Omit max to copy all events with value greater than or equal to min.

        By default min and max apply to the first value per event.
        Pass in value_index>0 to use a different value per event.

        This returns a new NumericEventList with a copy of events in the requested range.
        """
        value_column = value_index + 1
        if min:
            top_selector = self.event_data[:, value_column] >= min
        else:
            top_selector = True

        if max:
            bottom_selector = self.event_data[:, value_column] < max
        else:
            bottom_selector = True

        rows_in_range = top_selector & bottom_selector
        range_event_data = self.event_data[rows_in_range, :]
        return NumericEventList(range_event_data)
