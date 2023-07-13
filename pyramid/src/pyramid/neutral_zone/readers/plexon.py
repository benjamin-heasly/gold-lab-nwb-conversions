from types import TracebackType
from typing import ContextManager, Self

import numpy as np


# Representing Plexon file from C headers available here:
# http://www.plexon.com/software-downloads

GlobalHeader = np.dtype(
    [
        ('MagicNumber', 'uint32'),
        ('Version', 'int32'),
        ('Comment', 'S128'),
        ('ADFrequency', 'int32'),
        ('NumDSPChannels', 'int32'),
        ('NumEventChannels', 'int32'),
        ('NumSlowChannels', 'int32'),
        ('NumPointsWave', 'int32'),
        ('NumPointsPreThr', 'int32'),
        ('Year', 'int32'),
        ('Month', 'int32'),
        ('Day', 'int32'),
        ('Hour', 'int32'),
        ('Minute', 'int32'),
        ('Second', 'int32'),
        ('FastRead', 'int32'),
        ('WaveformFreq', 'int32'),
        ('LastTimestamp', 'float64'),

        # version >103
        ('Trodalness', 'uint8'),
        ('DataTrodalness', 'uint8'),
        ('BitsPerSpikeSample', 'uint8'),
        ('BitsPerSlowSample', 'uint8'),
        ('SpikeMaxMagnitudeMV', 'uint16'),
        ('SlowMaxMagnitudeMV', 'uint16'),

        # version 105
        ('SpikePreAmpGain', 'uint16'),

        # version 106
        ('AcquiringSoftware', 'S18'),
        ('ProcessingSoftware', 'S18'),

        ('Padding', 'S10'),

        # all version
        ('TSCounts', 'int32', (130,5)), # number of timestamps[channel][unit]
        ('WFCounts', 'int32', (130,5)), # number of waveforms[channel][unit]
        ('EVCounts', 'int32', (512,)),
    ]
)


class RawPlexonReader(ContextManager):
    """Read a Pleoxn .plx file sequentially, block by block.

    This borrows from the neo project's PlexonRawIO.
    https://github.com/NeuralEnsemble/python-neo/blob/master/neo/rawio/plexonrawio.py

    The reason we don't just use PlexonRawIO here is we want to move through the file sequentially,
    block by block over time. PlexonRawIO takes a different approach of indexing the whole file
    ahead of time and presenting a view per data type and channel, rather than sequentially.

    Thanks to the neo author Samuel Garcia for implementing a .plx file model in pure Python!
    """

    def __init__(self, plx_file: str) -> None:
        self.plx_file = plx_file

        self.plx_stream = None
        self.global_header = None

    def __enter__(self) -> Self:
        self.plx_stream = open(self.plx_file, 'br')
        self.global_header = self.consume_type(GlobalHeader)

        return self

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None
    ) -> bool | None:
        if self.plx_stream:
            self.plx_stream.close()
        self.plx_stream = None

    def consume_type(self, dtype: np.dtype):
        bytes = self.plx_stream.read(dtype.itemsize)
        item = np.frombuffer(bytes, dtype)[0]
        result = {}
        for name in dtype.names:
            value = item[name]
            if dtype[name].kind == 'S':
                value = value.decode('utf8')
                value = value.replace('\x03', '')
                value = value.replace('\x00', '')
            result[name] = value
        return result
