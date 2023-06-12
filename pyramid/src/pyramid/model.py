from typing import Any, Self
from dataclasses import dataclass

import numpy as np


class InteropData():
    """Utility methods to convert instances to and from standard types, for interop with other environments.

    The goal of this is to be able to read and write instances of InteropData classes as JSON or similar, 
    in such a way that the data could be shared with other environments, say Matlab.
    Automatic, field-by-field serializers would expose implementatoin details that don't make sense
    in other environments, like numpy array details in Matlab.  To avoid this, InteropData instances must 
    convert themselves to and from generic types that most environments (or JSON) can understand, like
    int, float, str, dict, and list.
    """

    def to_generic(self) -> Any:
        """Convert this instance to a standard type / collection like int, float, str, dict, or list."""
        pass

    @classmethod
    def from_generic(cls, generic) -> Self:
        """Create a new instance from a collection of standard types, as from to_standard()"""
        pass


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

    def to_generic(self) -> Any:
        return self.event_data.tolist()
    
    @classmethod
    def from_generic(cls, generic) -> Self:
        event_data = np.array(generic)
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
        """Remove events with values ouside the range [min, max] (inclusive).

        By default this applies only to the first value per event.
        Pass in value_index>0 to use a different value.
        This replaces the event_data with a filtered version.
        """
        filter_column = value_index + 1
        rows_in_range = (self.event_data[:, filter_column] >= min) & (self.event_data[:, filter_column] <= max)
        self.event_data = self.event_data[rows_in_range, :]
