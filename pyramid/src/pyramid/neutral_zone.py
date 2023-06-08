import numpy as np

class NumericEventList():
    # TODO: can this be a @dataclass?
    # from dataclasses import dataclass, field
    # maybe even a yaml_data, like in Proceed

    def __init__(self, event_data: np.ndarray) -> None:
        """Numeric event list can be represented as a packed 2D array.

        The event_data must have shape (n, 2+) where n is the number of events.
        Number of events is event_data.shape[0]
        Event timestamps are in event_data[:,0]
        Event values are in event_data[:,1]
        Optional additional values may be in event_data[:,2], event_data[:,3] ...
        Number of values per event is event_data.shape[1] - 1
        """
        self.event_data = event_data
        self.count = event_data.shape[0]
        self.values_per_event = event_data.shape[1] - 1

    def shift_times(self, shift: float) -> None:
        """Shift all event times by a constant.

        This modifies the event_data in place.
        """
        self.event_data[:,0] += shift
    
    def apply_offset_then_gain(self, offset: float, gain: float) -> None:
        """Transform all event data by a constant gain and offset.

        By convention: apply offset first, then gain.
        This makes it convenient subtract a baseline from eg ecodes, then scale to a fixed precision.

        This modifies the event_data in place.        
        """
        self.event_data[:,1:] += offset
        self.event_data[:,1:] *= gain

    def filter_min_and_max(self, min: float, max: float, value_index: int = 0) -> None:
        """Remove events with values ouside the range [min, max] (inclusive).

        This applies to the first event value by default, use value_index>0 to speficy another.
        This replaces the event_data with a filtered version.
        """
        filter_column = value_index + 1
        rows_in_range = self.event_data[:,filter_column] >= min & self.event_data[:,filter_column] <= max
        self.event_data = self.event_data[rows_in_range,:]
