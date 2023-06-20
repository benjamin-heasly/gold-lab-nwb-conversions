from typing import Any, Self
from dataclasses import dataclass, field

from pyramid.model.model import InteropData
from pyramid.model.numeric_events import NumericEventList, NumericEventSource

# Construct a trials "IOC container" / context declared in YAML.

# Read and write a Trial File as a JSON list of Trials
# Mixed Mode: https://pypi.org/project/json-stream/

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

    def __init__(
        self,
        start_source: NumericEventSource,
        start_value: float,
        wrt_source: NumericEventSource,
        wrt_value: float,
        start_value_index: int = 0,
        wrt_value_index: int = 0,
        trial_start_time: float = 0.0
    ) -> None:
        self.start_source = start_source
        self.start_value = start_value
        self.wrt_source = wrt_source
        self.wrt_value = wrt_value
        self.start_value_index = start_value_index
        self.wrt_value_index = wrt_value_index
        self.trial_start_time = trial_start_time

    def read_next(self) -> list[Trial]:
        """Poll the start source for new events, produce new trials whenever the chosen start_value arrives.

        This has side-effects on the start source and wrt source, potentially consuming data on each call.
        """
        new_start_events = self.start_source.read_next()
        if new_start_events and new_start_events.event_count():
            next_start_times = new_start_events.get_times_of(self.start_value, self.start_value_index)
            if next_start_times.size > 0:
                trials = []
                for next_start_time in next_start_times:
                    self.wrt_source.read_until_time(next_start_time)
                    trial = self.make_trial(next_start_time)
                    trials.append(trial)
                    self.trial_start_time = next_start_time
                return trials        
        return None

    def read_last(self) -> Trial:
        """Make a best effort to make a trial with whatever's left on the start and wrt sources.

        This has side-effects on the start source and wrt source, potentially consuming data on each call.        
        """
        self.start_source.read_next()
        self.wrt_source.read_next()
        trial = self.make_trial(None)
        return trial

    def make_trial(self, next_start_time: float, default_wrt_time: float = 0.0) -> Trial:
        """Make a new Trial starting where the last trial ended.
        
        This queries the wrt_source for a wrt time at or after the current trial_start_time,
        and strictly before the given next_start_time.
        next_start_time can be None to take whatever's after trial_start_time.
        
        This should be safe to call repeatedly, without side effects.

        Returns a new Trial spanning the current trial_start_time up to the given next_start_time.
        """
        wrt_times = self.wrt_source.event_list.get_times_of(
            self.wrt_value,
            self.wrt_value_index,
            start_time = self.trial_start_time,
            end_time = next_start_time
        )
        if wrt_times.size > 0:
            wrt_time = wrt_times.min()
        else:
            wrt_time = default_wrt_time

        trial = Trial(start_time=self.trial_start_time, end_time=next_start_time, wrt_time=wrt_time)
        return trial

    def discard_before(self, time: float):
        """Let event sources discard data no longer needed."""
        self.start_source.discard_before(time)
        self.wrt_source.discard_before(time)


class TrialExtractor():
    """Follow a trial delimiter, waiting for new trials, populating each one with data."""

    def __init__(
        self,
        delimiter: TrialDelimiter,
        numeric_sources: dict[str, NumericEventSource] = {}
    ) -> None:
        self.delimiter = delimiter
        self.numeric_sources = numeric_sources

    def read_next(self) -> list[Trial]:
        """Poll the delimiter for new trials, populate each new trial with data from configured sources.

        This has side-effects on the delimiter and other sources, potentially consuming data on each call.
        """
        new_trials = self.delimiter.read_next()
        if new_trials:
            for trial in new_trials:
                self.populate_trial(trial)
                self.discard_before(trial.start_time)
            return new_trials
        else:
            return None

    def read_last(self) -> Trial:
        """Poll the delimiter for whatever's left, populate this last trial with whatever's left from configured sources."""
        last_trial = self.delimiter.read_last()
        self.populate_trial(last_trial)
        self.discard_before(last_trial.start_time)
        return last_trial

    def populate_trial(self, trial: Trial):
        """Fill in the given trial with data from configured sources, in the trial's time range.

        This causes the configured sources to "catch up" to the trial's end_time.
        """
        for name, source in self.numeric_sources.items():
            if trial.end_time:
                source.read_until_time(trial.end_time)
            else:
                source.read_next()
            events = source.event_list.copy_time_range(trial.start_time, trial.end_time)
            events.shift_times(-trial.wrt_time)
            trial.add_numeric_events(name, events)

    def discard_before(self, time: float):
        """Let event sources discard data no longer needed."""
        self.delimiter.discard_before(time)
        for source in self.numeric_sources.values():
            source.discard_before(time)
