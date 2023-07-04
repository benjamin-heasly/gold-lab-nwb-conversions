from typing import Self
import time

from pyramid.neutral_zone.readers.readers import Reader
from pyramid.model.model import BufferData

class DelaySimulatorReader(Reader):
    """Simulate delay between events so offline plays back sort of like online.
    """

    def __init__(self, reader: Reader) -> None:
        self.reader = reader
        self.stashed_result = None
        self.stash_until = None
        self.start_time = None

    def __eq__(self, other: object) -> bool:
        """Compare readers field-wise, to support use of this class in tests."""
        if isinstance(other, self.__class__):
            return self.reader == other.reader
        else:  # pragma: no cover
            return False

    def __enter__(self) -> Self:
        self.start_time = time.time()
        return self.reader.__enter__()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.reader.__exit__(exc_type, exc_value, traceback)

    def read_next(self) -> dict[str, BufferData]:
        if self.stashed_result:
            elapsed = time.time() - self.start_time
            if elapsed >= self.stash_until:
                stashed = self.stashed_result
                self.stashed_result = None
                return stashed
            else:
                return None

        next_result = self.reader.read_next()
        if next_result:
            end_times = [result.get_end_time() for result in next_result.values()]
            self.stash_until = max(end_times)
            self.stashed_result = next_result

    def get_initial(self) -> dict[str, BufferData]:
        return self.reader.get_initial()
