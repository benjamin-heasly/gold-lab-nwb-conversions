from typing import Self

import numpy as np

from pyramid.neutral_zone.readers.readers import Reader
from pyramid.model.numeric_events import NumericEventList

# route events to buffer
# route same events two buffers
# routed events are independent copies

# router catches reader errors and circuit-breaks
# router tolerates reader empty reads, gets it next time

# router transforms data
# router catchers transformer errors and skips


class FakeNumericEventReader(Reader):

    def __init__(
        self,
        script=[[[0, 0]],
                [[1, 10]],
                [[2, 20]],
                [[3, 30]],
                [[4, 40]],
                [[5, 50]],
                [[6, 60]],
                [[7, 70]],
                [[8, 80]],
                [[9, 90]]]
    ) -> None:
        self.index = -1
        self.script = script

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass

    def read_next(self) -> dict[str, NumericEventList]:
        # Incrementing this index is like consuming a system or library resource:
        # - advance a file cursor
        # - increment past a file data block
        # - poll a network connection
        self.index += 1

        # Return dummy events from the contrived script, which might contain gaps and require retries.
        if self.index < len(self.script) and self.script[self.index]:
            return NumericEventList(np.array(self.script[self.index]))
        else:
            return None
