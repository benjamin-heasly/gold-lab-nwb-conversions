from typing import Any, Self
from dataclasses import dataclass, field

import numpy as np


class InteropData():
    """Utility methods to convert instances to and from standard types, for interop with other environments.

    The goal of this is to be able to read and write instances of InteropData classes as JSON or similar, 
    in such a way that the data could be shared with other environments, say Matlab.
    Automatic, field-by-field serializers would expose implementatoin details that don't make sense
    in other environments, like numpy array details in Matlab.  To avoid this, InteropData instances must 
    convert themselves to and from standard types that most environments (or JSON) can understand, like
    int, float, str, dict, and list.
    """

    def to_interop(self) -> Any:
        """Convert this instance to a standard types / collections like int, float, str, dict, or list."""
        pass

    @classmethod
    def from_interop(cls, interop) -> Self:
        """Create a new instance of this class from standard types / collections, as from to_interop()"""
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

    def __eq__(self, other: object) -> bool:
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


class NumericEventSource():
    """Interface for queryable sources of numeric event lists, like online streams or data files."""

    def query(start_time: float, end_time: float) -> NumericEventList:
        """Buffer enough data from the source to return events in the half-open interval [start_time to end_time).

        I imagine we'll call this repeatedly, with end_time of the first call becoming start_time in the next call.
        If an event happens right at start_time or end_time, if might get redundantly returned in both calls.
        So by convention, let's make start_time inclusing and end_time exclusive.

        This method may block until it's able to report on the whole query interval.
        The idea is by the time we call query, we think a trial has been complted.
        So blocking here should just be waiting for files or socket buffers to fill up and not take long (famous last words?).
        """
        pass

    def check_next(timeout: float) -> NumericEventList:
        """Buffer and return the next event, if any.

        This method must not block indefinitely.  Instead, return None after timeout seconds.
        The idea is we'll want to interleave waiting for the next trial, GUI updates, and other processing.
        """
        pass


@dataclass
class Trial(InteropData):
    """A delimited part of the timeline with named event, signal, and computed data from the same time range."""

    start_time: float
    """The begining of the trial in time, often the time of a delimiting event."""

    end_time: float
    """The end of the trial in time, often the time of the next delimiting event after start_time."""

    wrt_time: float
    """The "zero" time subtracted from events and signals assigned to this trial, often between start_time and end_time."""

    numeric_events: dict[str, NumericEventList] = field(default_factory=dict)
    """Named lists of numeric events assigned to this trial."""

    def to_interop(self) -> Any:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "wrt_time": self.wrt_time,
            "numeric_events": {name: event_list.to_interop() for (name, event_list) in self.numeric_events.items()}
        }

    @classmethod
    def from_interop(cls, interop) -> Self:
        trial = Trial(interop["start_time"], interop["end_time"], interop["wrt_time"])
        for (name, event_list) in interop["numeric_events"].items():
            trial.add_numeric_events(name, NumericEventList.from_interop(event_list))
        return trial

    def add_numeric_events(self, name: str, event_list: NumericEventList):
        """Add a numeric event list to this trial, as-is."""
        self.numeric_events[name] = event_list

    def query_numeric_event_source(self, name: str, event_source: NumericEventSource, timeout: float):
        """Query the given event source for events to assign to this trial, align the event times to wrt_time."""
        event_list = event_source.query(self.start_time, self.end_time, timeout)
        event_list.shift_times(-self.wrt_time)
        self.add_numeric_events(name, event_list)
