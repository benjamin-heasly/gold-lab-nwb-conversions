from typing import Any, Self
from dataclasses import dataclass, field
import logging

from pyramid.model.model import DynamicImport, Buffer, BufferData
from pyramid.model.events import NumericEventList
from pyramid.model.signals import SignalChunk


@dataclass
class Trial():
    """A delimited part of the timeline with named event, signal, and computed data from the same time range."""

    start_time: float
    """The begining of the trial in time, often the time of a delimiting event."""

    end_time: float
    """The end of the trial in time, often the time of the next delimiting event after start_time."""

    wrt_time: float = 0.0
    """The "zero" time subtracted from events and signals assigned to this trial, often between start_time and end_time."""

    numeric_events: dict[str, NumericEventList] = field(default_factory=dict)
    """Named lists of numeric events assigned to this trial."""

    signals: dict[str, SignalChunk] = field(default_factory=dict)
    """Named signal chunks assigned to this trial."""

    enhancements: dict[str, Any] = field(default_factory=dict)
    """Name-data pairs, to add to the trial."""

    enhancement_categories: dict[str, list[str]] = field(default_factory=dict)
    """Enhancement names grouped by category, like "id", "value", or "time"."""

    def add_buffer_data(self, name: str, data: BufferData) -> bool:
        """Add named data to this trial, of a specific buffer data type that requires conversion before writing."""
        if isinstance(data, NumericEventList):
            self.numeric_events[name] = data
            return True
        elif isinstance(data, SignalChunk):
            self.signals[name] = data
            return True
        else:
            logging.warning(
                f"Data for name {name} not added to trial because class {data.__class__.__name__} is not supported.")
            return False

    def add_enhancement(self, name: str, data: Any, category: str = "value") -> bool:
        """Add a name-data pair to the trial.

        Enhancements are added to the trial as name-data pairs.  The names must be unique per trial.

        The names are grouped in categories that inform downstream utilities how to interpret the data, for example:
         - "value": (default) discrete or continuous score or metric like a distance, a duration, etc.
         - "id": nominal or ordinal label for the trial -- a key you might use to group or sort trials
         - "time": list of timestamps for when a named event occurred during the trial -- zero or more occurrences

        The given data should be of a simple type that doesn't require special conversion to/from file, for example:
         - str
         - int
         - float
         - list (can be nested)
         - dict (can be nested)

        If the given data is one of the BufferData types, like NumericEventList or SignalChunk,
        it will be passed to add_buffer_data() instead of being saved as an enchancement.
        """
        if isinstance(data, BufferData):
            return self.add_buffer_data(name, data)
        else:
            if category not in self.enhancement_categories:
                self.enhancement_categories[category] = []
            if name not in self.enhancement_categories[category]:
                self.enhancement_categories[category].append(name)
            self.enhancements[name] = data
            return True

    def get_enhancement(self, name: str, default: Any = None) -> Any:
        """Get the value of a previously added enhancement, or return the given default."""
        return self.enhancements.get(name, default)

    def get_one(self, name: str, default: Any = None, index: int = 0) -> Any:
        """Get one element from of a list previously added as an enhancement, or return the given default."""
        data = self.get_enhancement(name, default)
        if isinstance(data, list):
            if len(data):
                # One list element.
                return data[index]
            else:
                # Empty list!
                return default
        else:
            # Data is already a scalar.
            return data


class TrialDelimiter():
    """Monitor a "start" event buffer, making new trials as delimiting events arrive."""

    def __init__(
        self,
        start_buffer: Buffer,
        start_value: float,
        start_value_index: int = 0,
        trial_start_time: float = 0.0,
        trial_count: int = 0,
        trial_log_mod: int = 50
    ) -> None:
        self.start_buffer = start_buffer
        self.start_value = start_value
        self.start_value_index = start_value_index
        self.trial_start_time = trial_start_time
        self.trial_count = trial_count
        self.trial_log_mod = trial_log_mod

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

    def next(self) -> dict[int, Trial]:
        """Check the start buffer for start events, produce new trials as new start events arrive.

        This has the side-effects of incrementing trial_start_time and trial_count.
        """
        trials = {}
        next_start_times = self.start_buffer.data.get_times_of(self.start_value, self.start_value_index)
        for next_start_time in next_start_times:
            if next_start_time > self.trial_start_time:
                trial = Trial(start_time=self.trial_start_time, end_time=next_start_time)
                trials[self.trial_count] = trial

                self.trial_start_time = next_start_time
                self.trial_count += 1
                if self.trial_count % self.trial_log_mod == 0:
                    logging.info(f"Delimited {self.trial_count} trials.")

        return trials

    def last(self) -> tuple[int, Trial]:
        """Make a best effort to make a trial with whatever's left on the start buffer.

        This has the side effect of incrementing trial_count.
        """
        trial = Trial(start_time=self.trial_start_time, end_time=None)
        last_trial = (self.trial_count, trial)
        self.trial_count += 1
        logging.info(f"Delimited {self.trial_count} trials (last one).")
        return last_trial

    def discard_before(self, time: float):
        """Let event buffer discard data no longer needed."""
        self.start_buffer.data.discard_before(time)


class TrialEnhancer(DynamicImport):
    """Compute new name-value pairs save with each trial."""

    def enhance(
        self,
        trial: Trial,
        trial_number: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        """Add simple data types to a trial's enchancements.

        Implementations should add to the given trial using either or:
         - trial.add_enhancement(name, data)
         - trial.add_enhancement(name, data, category)

        The data values must be standard, portable data types like int, float, or string, or lists and dicts of these types.
        Other data types might not survive being written to or read from the trial file.
        """
        raise NotImplementedError  # pragma: no cover


class TrialExtractor():
    """Populate trials with WRT-aligned data from named buffers."""

    def __init__(
        self,
        wrt_buffer: Buffer,
        wrt_value: float,
        wrt_value_index: int = 0,
        named_buffers: dict[str, Buffer] = {},
        enhancers: list[TrialEnhancer] = []
    ) -> None:
        self.wrt_buffer = wrt_buffer
        self.wrt_value = wrt_value
        self.wrt_value_index = wrt_value_index
        self.named_buffers = named_buffers
        self.enhancers = enhancers

    def __eq__(self, other: object) -> bool:
        """Compare extractors field-wise, to support use of this class in tests."""
        if isinstance(other, self.__class__):
            return (
                self.wrt_buffer == other.wrt_buffer
                and self.wrt_value == other.wrt_value
                and self.wrt_value_index == other.wrt_value_index
                and self.named_buffers == other.named_buffers
                and self.enhancers == other.enhancers
            )
        else:  # pragma: no cover
            return False

    def populate_trial(
        self,
        trial: Trial,
        trial_number: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ):
        """Fill in the given trial with data from configured buffers, in the trial's time range."""
        trial_wrt_times = self.wrt_buffer.data.get_times_of(
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
            data = buffer.data.copy_time_range(trial.start_time, trial.end_time)
            data.shift_times(-trial.wrt_time)
            trial.add_buffer_data(name, data)

        for enhancer in self.enhancers:
            try:
                enhancer.enhance(trial, trial_number, experiment_info, subject_info)
            except:
                logging.error(f"Error applying enhancer {enhancer.__class__.__name__} to trial {trial_number}.", exc_info=True)
                continue

    def discard_before(self, time: float):
        """Let event wrt and named buffers discard data no longer needed."""
        self.wrt_buffer.data.discard_before(time)
        for buffer in self.named_buffers.values():
            buffer.data.discard_before(time)
