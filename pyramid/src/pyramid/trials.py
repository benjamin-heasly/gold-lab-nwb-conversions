from typing import Any, Self
from dataclasses import dataclass, field

from pyramid.model import InteropData
from pyramid.numeric_events import NumericEventList, NumericEventSource


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


class TrialDelimiter():
    """Follow a chosen event source, waiting for events that delimit trials in time."""

    def __init__(self, event_source: NumericEventSource, event_values: list[Any] = [], start_time: float = 0.0) -> None:
        self.event_source = event_source
        self.event_values = event_values
        self.start_time = start_time

    def next_trial(timeout: float = 0.025) -> Trial:
        # TODO: wait on an event source for up to timeout seconds
        return Trial()


class TrialExtracor():
    # Read and write a Trial File as a JSON list of Trials
    # Mixed Mode: https://pypi.org/project/json-stream/

    def query_numeric_event_source(self, name: str, event_source: NumericEventSource, timeout: float):
        """Query the given event source for events to assign to this trial, align the event times to wrt_time."""
        event_list = event_source.query(self.start_time, self.end_time, timeout)
        event_list.shift_times(-self.wrt_time)
        self.add_numeric_events(name, event_list)
