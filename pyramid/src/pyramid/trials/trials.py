from typing import Any, Self
from dataclasses import dataclass, field

from pyramid.model.model import InteropData
from pyramid.model.events import NumericEventList, NumericEventBuffer

# Construct a trials "IOC container" / context declared in YAML.


@dataclass
class Trial(InteropData):
    """A delimited part of the timeline with named event, signal, and computed data from the same time range."""

    start_time: float
    """The begining of the trial in time, often the time of a delimiting event."""

    end_time: float
    """The end of the trial in time, often the time of the next delimiting event after start_time."""

    wrt_time: float = 0.0
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
    """Monitor a "start" event buffer, making new trials as delimiting events arrive."""

    def __init__(
        self,
        start_buffer: NumericEventBuffer,
        start_value: float,
        start_value_index: int = 0,
        trial_start_time: float = 0.0,
        trial_count: int = 0
    ) -> None:
        self.start_buffer = start_buffer
        self.start_value = start_value
        self.start_value_index = start_value_index
        self.trial_start_time = trial_start_time
        self.trial_count = trial_count

    def __eq__(self, other: object) -> bool:
        """Compare delimiters field-wise, to support use of this class in tests."""
        if isinstance(other, self.__class__):
            return (
                self.start_buffer == other.start_buffer
                and self.start_value == other.start_value
                and self.start_value_index == other.start_value_index
                and self.trial_start_time == other.trial_start_time
                and self.trial_count == other.trial_count
            )
        else:  # pragma: no cover
            return False

    def next(self) -> list[Trial]:
        """Check the start buffer for start events, produce new trials as new start events arrive.

        This has the side-effects of incrementing trial_start_time and trial_count.
        """
        trials = []
        next_start_times = self.start_buffer.event_list.get_times_of(self.start_value, self.start_value_index)
        for next_start_time in next_start_times:
            if next_start_time > self.trial_start_time:
                trial = Trial(start_time=self.trial_start_time, end_time=next_start_time)
                trials.append(trial)
                self.trial_start_time = next_start_time
                self.trial_count += 1
        return trials

    def last(self) -> Trial:
        """Make a best effort to make a trial with whatever's left on the start buffer.

        This has the side effect of incrementing trial_count.
        """
        trial = Trial(start_time=self.trial_start_time, end_time=None)
        self.trial_count += 1
        return trial

    def discard_before(self, time: float):
        """Let event buffer discard data no longer needed."""
        self.start_buffer.discard_before(time)


class TrialExtractor():
    """Populate trials with WRT-aligned data from named buffers."""

    def __init__(
        self,
        wrt_buffer: NumericEventBuffer,
        wrt_value: float,
        wrt_value_index: int = 0,
        named_buffers: dict[str, NumericEventBuffer] = {}
    ) -> None:
        self.wrt_buffer = wrt_buffer
        self.wrt_value = wrt_value
        self.wrt_value_index = wrt_value_index
        self.named_buffers = named_buffers

    def __eq__(self, other: object) -> bool:
        """Compare extractors field-wise, to support use of this class in tests."""
        if isinstance(other, self.__class__):
            return (
                self.wrt_buffer == other.wrt_buffer
                and self.wrt_value == other.wrt_value
                and self.wrt_value_index == other.wrt_value_index
                and self.named_buffers == other.named_buffers
            )
        else:  # pragma: no cover
            return False

    def populate_trial(self, trial: Trial):
        """Fill in the given trial with data from configured buffers, in the trial's time range."""
        trial_wrt_times = self.wrt_buffer.event_list.get_times_of(
            self.wrt_value,
            self.wrt_value_index,
            trial.start_time,
            trial.end_time
        )
        if trial_wrt_times.size > 0:
            trial.wrt_time = trial_wrt_times.min()
        else:
            trial.wrt_time = 0.0

        for name, buffer in self.named_buffers.items():
            # TODO: will be other buffer types here, besides NumericEventBuffer
            events = buffer.event_list.copy_time_range(trial.start_time, trial.end_time)
            events.shift_times(-trial.wrt_time)
            trial.add_numeric_events(name, events)

    def discard_before(self, time: float):
        """Let event wrt and named buffers discard data no longer needed."""
        self.wrt_buffer.discard_before(time)
        for buffer in self.named_buffers.values():
            buffer.discard_before(time)
