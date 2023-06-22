from typing import Self
import time

from pyramid.model.numeric_events import NumericEventList, NumericEventReader

# Delay simulator string event reader?
# Delay simulator signal reader?

class DelaySimulatorNumericEventReader(NumericEventReader):
    """Read numeric events from another reader, and simulate delay between them.
    """

    def __init__(self, reader: NumericEventReader) -> None:
        self.reader = reader
        self.stashed_events = None
        self.start_time = None

    def __enter__(self) -> Self:
        self.start_time = time.time()
        return self.reader.__enter__()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.reader.__exit__(exc_type, exc_value, traceback)

    def read_next(self, timeout: float) -> NumericEventList:
        if self.stashed_events:
            elapsed = time.time() - self.start_time
            stash_until = self.stashed_events.get_times().max()
            if elapsed >= stash_until:
                stashed = self.stashed_events
                self.stashed_events = None
                return stashed
            else:
                return None

        self.stashed_events = self.reader.read_next(timeout)
