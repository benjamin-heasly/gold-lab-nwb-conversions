from typing import Any


class Trial():
    # TODO: this can be a @dataclass
    # from dataclasses import dataclass, field
    # maybe even a yaml_data, like in Proceed

    def __init__(self, start_time: float, end_time: float, wrt_time: float) -> None:
        self.start_time = start_time
        self.end_time = end_time
        self.wrt_time = wrt_time
        self.data = {}

    def add_data(self, name: str, data: Any):
        # TODO: query an event or signal source for start-end range and wrt-subtract the times
        self.data[name] = data


class TrialsController():

    def next(timeout: float = 0.025) -> Trial:
        # TODO: wait on an event source for up to timeout seconds
        return Trial()
