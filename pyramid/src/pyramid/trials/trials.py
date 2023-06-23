from typing import Any, Self
from dataclasses import dataclass, field

from pyramid.model.model import InteropData
from pyramid.model.numeric_events import NumericEventList, NumericEventBuffer

# Construct a trials "IOC container" / context declared in YAML.


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
    """Monitor "start" and "wrt" event buffers, making new trials as delimiting events arrive."""

    def __init__(
        self,
        start_buffer: NumericEventBuffer,
        start_value: float,
        wrt_buffer: NumericEventBuffer,
        wrt_value: float,
        start_value_index: int = 0,
        wrt_value_index: int = 0,
        trial_start_time: float = 0.0,
        trial_count: int = 0
    ) -> None:
        self.start_buffer = start_buffer
        self.start_value = start_value
        self.wrt_buffer = wrt_buffer
        self.wrt_value = wrt_value
        self.start_value_index = start_value_index
        self.wrt_value_index = wrt_value_index
        self.trial_start_time = trial_start_time
        self.trial_count = trial_count

    def next(self) -> list[Trial]:
        """Check the start buffer for start events, produce new trials as new start events arrive.

        This has side-effect of incrementing trial_start_time and trial_count.
        """
        trials = []
        next_start_times = self.start_buffer.event_list.get_times_of(self.start_value, self.start_value_index)
        for next_start_time in next_start_times:
            if next_start_time > self.trial_start_time:
                trial = self.make_trial(next_start_time)
                trials.append(trial)
                self.trial_start_time = next_start_time
                self.trial_count += 1

        return trials

    def last(self) -> Trial:
        """Make a best effort to make a trial with whatever's left on the start and wrt sources.

        This has side-effects on the start source and wrt source, potentially consuming data on each call.
        """
        trial = self.make_trial(None)
        self.trial_count += 1
        return trial

    def make_trial(self, next_start_time: float, default_wrt_time: float = 0.0) -> Trial:
        """Make a new Trial starting where the last trial ended.

        This queries the wrt_buffer for a wrt time in [self.trial_start_time, next_start_time).
        next_start_time can be None to take whatever's at or after trial_start_time.

        This should be safe to call repeatedly, without side effects.

        Returns a new Trial spanning the current trial_start_time up to the given next_start_time.
        """
        wrt_times = self.wrt_buffer.event_list.get_times_of(
            self.wrt_value,
            self.wrt_value_index,
            start_time=self.trial_start_time,
            end_time=next_start_time
        )
        if wrt_times.size > 0:
            wrt_time = wrt_times.min()
        else:
            wrt_time = default_wrt_time

        trial = Trial(start_time=self.trial_start_time, end_time=next_start_time, wrt_time=wrt_time)
        return trial

    def discard_before(self, time: float):
        """Let event buffers discard data no longer needed."""
        self.start_buffer.discard_before(time)
        self.wrt_buffer.discard_before(time)


class TrialExtractor():
    """Monitor a trial delimiter, waiting for new trials, populating each one with data from other buffers."""

    def __init__(
        self,
        delimiter: TrialDelimiter,
        buffers: dict[str, NumericEventBuffer] = {}
    ) -> None:
        self.delimiter = delimiter
        self.buffers = buffers

    def get_progress_info(self) -> dict[str, Any]:
        """Return a dictionary of trial extraction progress info."""
        return {
            "trial_count": self.delimiter.trial_count
        }

    def next(self) -> list[Trial]:
        """Query the delimiter for new trials, populate each new trial with data from other buffers.

        This has side-effects on the delimiter, incrementing trial start time and trial count.
        """
        new_trials = self.delimiter.next()
        if new_trials:
            for trial in new_trials:
                self.populate_trial(trial)
                self.discard_before(trial.start_time)
            return new_trials
        else:
            return None

    def last(self) -> Trial:
        """Query the delimiter for whatever's left, populate this last trial with whatever's left from other sources."""
        last_trial = self.delimiter.last()
        self.populate_trial(last_trial)
        self.discard_before(last_trial.start_time)
        return last_trial

    def populate_trial(self, trial: Trial):
        """Fill in the given trial with data from configured buffers, in the trial's time range."""
        for name, buffer in self.buffers.items():
            # TODO: will be other buffer types here, besides NumericEventBuffer
            events = buffer.event_list.copy_time_range(trial.start_time, trial.end_time)
            events.shift_times(-trial.wrt_time)
            trial.add_numeric_events(name, events)

    def discard_before(self, time: float):
        """Let event sources discard data no longer needed."""
        self.delimiter.discard_before(time)
        for source in self.buffers.values():
            source.discard_before(time)
