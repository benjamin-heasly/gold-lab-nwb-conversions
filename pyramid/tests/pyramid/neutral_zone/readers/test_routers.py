import numpy as np

from pyramid.neutral_zone.readers.readers import Reader
from pyramid.model.numeric_events import NumericEventList

# TODO: missing coverage:
# route events to buffer
# route events to missing buffer
# route events missing from results
# route same events two buffers
# routed events are independent copies
#
# router catches reader errors and circuit-breaks
# router tolerates reader empty reads and retries n times
# router reads until target time
#
# router transforms data
# router catchers transformer errors and skips


class FakeNumericEventReader(Reader):

    def __init__(self, script=[]) -> None:
        self.index = -1
        self.script = script

    def read_next(self) -> dict[str, NumericEventList]:
        # Incrementing this index is like consuming a system or library resource:
        # - advance a file cursor
        # - increment past a file data block
        # - poll a network connection
        self.index += 1

        # Return dummy events from the contrived script, which might contain gaps and require retries.
        if self.index < len(self.script) and self.script[self.index]:
            return {
                "events": NumericEventList(np.array(self.script[self.index]))
            }
        else:
            return None
