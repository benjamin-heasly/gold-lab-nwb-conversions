from typing import Any


class TrialDelimiter():
    # Read and write a Trial File as a JSON list of Trials
    # Mixed Mode: https://pypi.org/project/json-stream/

    def next(timeout: float = 0.025) -> Trial:
        # TODO: wait on an event source for up to timeout seconds
        return Trial()
