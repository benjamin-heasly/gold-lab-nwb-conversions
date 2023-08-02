import logging
from types import TracebackType
from typing import Self, ContextManager
from collections.abc import Iterator
from pathlib import Path

import json
import numpy as np

from pyramid.model.events import NumericEventList
from pyramid.model.signals import SignalChunk
from pyramid.trials.trials import Trial


class TrialFile(ContextManager):
    """Write and read Pyramid Trials to and from a file.

    The TrialFile class itself is an abstract interface, to be implemented using various file formats
    like JSON and HDF5.

    It's up to each implementation to handle data mapping/conversion details.
    Each trial written with append_trial() should be recovered when returned from read_trials(),
    such that original_trial == recovered_trial.
    """

    def __enter__(self) -> Self:
        """Create a new, empty file for writing trials into."""
        raise NotImplementedError  # pragma: no cover

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None
    ) -> bool | None:
        """If needed, clean up resources used while writing trials to disk."""
        pass

    def append_trial(self, trial: Trial) -> None:
        """Write the given trial to the end of the file on disk.

        Implementations should try to leave a well-formed file on disk after each call to append_trial.
        This should allow calls to read_trials() to be interleaved with calls to append_trial(), if needed.

        For example, the file could be opened and closed during each append_trial(),
        as opposed to being opened once during __enter__() and held open until __exit__().
        """
        raise NotImplementedError  # pragma: no cover

    def read_trials(self) -> Iterator[Trial]:
        """Yield a sequence of trials from the file on disk, one at a time, in order.

        Implementations should implement this as a Python generator, using the yield keyword.
        https://wiki.python.org/moin/Generators

        It's OK to only return trials that were written to disk as of when read_trials() was first called.
        The generator doesn't need to check if new trials were written concurrently during iteration.
        """
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def for_file_suffix(cls, file_name: str) -> Self:
        suffix = Path(file_name).suffix.lower()
        if suffix in {".json", ".jsonl"}:
            return JsonTrialFile(file_name)
        # elif suffix == ".hd5":
        #     return Hdf5TrialFile(file_name)
        else:
            raise NotImplementedError(f"Unsupported trial file suffix: {suffix}")


class JsonTrialFile(TrialFile):
    """Text-based trial file using one line of JSON per trial.

    This trial file implementation uses the concept of "JSON Lines" to support large, streamable JSON files.
    https://jsonlines.org/
    """

    def __init__(self, file_name: str) -> None:
        self.file_name = file_name

    def __enter__(self) -> Self:
        with open(self.file_name, "w", encoding="utf-8"):
            logging.info(f"Creating empty JSON trial file: {self.file_name}")
        return self

    def append_trial(self, trial: Trial) -> None:
        trial_dict = self.dump_trial(trial)
        trial_json = json.dumps(trial_dict)
        with open(self.file_name, 'a', encoding="utf-8") as f:
            f.write(trial_json + "\n")

    def read_trials(self) -> Iterator[Trial]:
        with open(self.file_name, 'r', encoding="utf-8") as f:
            for json_line in f:
                trial_dict = json.loads(json_line)
                yield self.load_trial(trial_dict)

    def dump_numeric_event_list(self, numeric_event_list: NumericEventList) -> list:
        return numeric_event_list.event_data.tolist()

    def load_numeric_event_list(self, raw_list: list) -> NumericEventList:
        return NumericEventList(np.array(raw_list))

    def dump_signal_chunk(self, signal_chunk: SignalChunk) -> dict:
        return {
            "signal_data": signal_chunk.sample_data.tolist(),
            "sample_frequency": signal_chunk.sample_frequency,
            "first_sample_time": signal_chunk.first_sample_time,
            "channel_ids": signal_chunk.channel_ids
        }

    def load_signal_chunk(self, raw_dict: dict) -> SignalChunk:
        return SignalChunk(
            sample_data=np.array(raw_dict["signal_data"]),
            sample_frequency=raw_dict["sample_frequency"],
            first_sample_time=raw_dict["first_sample_time"],
            channel_ids=raw_dict["channel_ids"]
        )

    def dump_trial(self, trial: Trial) -> dict:
        raw_dict = {
            "start_time": trial.start_time,
            "end_time": trial.end_time,
            "wrt_time": trial.wrt_time
        }

        if trial.numeric_events:
            raw_dict["numeric_events"] = {
                name: self.dump_numeric_event_list(event_list) for name, event_list in trial.numeric_events.items()
            }

        if trial.signals:
            raw_dict["signals"] = {
                name: self.dump_signal_chunk(signal_chunk) for name, signal_chunk in trial.signals.items()
            }

        if trial.enhancements:
            raw_dict["enhancements"] = trial.enhancements

        return raw_dict

    def load_trial(self, raw_dict) -> Trial:
        numeric_events = {
            name: self.load_numeric_event_list(event_data)
            for name, event_data in raw_dict.get("numeric_events", {}).items()
        }

        signals = {
            name: self.load_signal_chunk(signal_data)
            for name, signal_data in raw_dict.get("signals", {}).items()
        }

        trial = Trial(
            start_time=raw_dict["start_time"],
            end_time=raw_dict["end_time"],
            wrt_time=raw_dict["wrt_time"],
            numeric_events=numeric_events,
            signals=signals,
            enhancements=raw_dict.get("enhancements", {})
        )
        return trial

# TODO: Hdf5TrialFile !