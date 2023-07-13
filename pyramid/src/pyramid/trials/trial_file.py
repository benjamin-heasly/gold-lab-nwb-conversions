from types import TracebackType
from typing import Self, ContextManager
import json

from pyramid.trials.trials import Trial


class TrialFileWriter(ContextManager):
    """Incrementally write trials to a file as a JSON list.
    
    Appends trials incrementally to a JSON file.
    Each trial will be dumped to string independently and written on its own line.
    This is similar to the "JSON Lines" concept: https://jsonlines.org/

    However, we also want to produce valid JSON for reading  by eg Matlab.
    So this also adds JSON list delimiters:
     - "[" on the first line
     - "," at the end of each trial line except the last line
     - "]" at the end of the last trial line

    This implements the Python context manager procol.
    So if used with "with", it should take care of adding delimiters.
    """

    def __init__(self, trial_file: str) -> None:
        self.trial_file = trial_file
        self.file_stream = None
        self.trial_separator = "\n"

    def __enter__(self) -> Self:
        self.file_stream = open(self.trial_file, "w", encoding="utf-8")
        self.file_stream.write("[")
        return self

    def append_trial(self, trial: Trial) -> None:
        trial_json = json.dumps(trial.to_interop())
        self.file_stream.write(self.trial_separator)
        self.file_stream.write(trial_json)
        self.trial_separator = ",\n"

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None
    ) -> bool | None:
        if self.file_stream:
            self.file_stream.write("\n]\n")
            self.file_stream.close()
        self.file_stream = None
