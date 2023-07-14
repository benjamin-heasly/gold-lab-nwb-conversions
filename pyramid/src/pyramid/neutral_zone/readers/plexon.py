from types import TracebackType
from typing import ContextManager, Self, Any

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
        ('TSCounts', 'int32', (130, 5)),  # number of timestamps[channel][unit]
        ('WFCounts', 'int32', (130, 5)),  # number of waveforms[channel][unit]
        ('EVCounts', 'int32', (512,)),
    ]
)

DspChannelHeader = np.dtype(
    [
        ('Name', 'S32'),
        ('SIGName', 'S32'),
        ('Channel', 'int32'),
        ('WFRate', 'int32'),
        ('SIG', 'int32'),
        ('Ref', 'int32'),
        ('Gain', 'int32'),
        ('Filter', 'int32'),
        ('Threshold', 'int32'),
        ('Method', 'int32'),
        ('NUnits', 'int32'),
        ('Template', 'uint16', (5, 64)),
        ('Fit', 'int32', (5,)),
        ('SortWidth', 'int32'),
        ('Boxes', 'uint16', (5, 2, 4)),
        ('SortBeg', 'int32'),
        # version 105
        ('Comment', 'S128'),
        # version 106
        ('SrcId', 'uint8'),
        ('reserved', 'uint8'),
        ('ChanId', 'uint16'),

        ('Padding', 'int32', (10,)),
    ]
)

EventChannelHeader = np.dtype(
    [
        ('Name', 'S32'),
        ('Channel', 'int32'),
        # version 105
        ('Comment', 'S128'),
        # version 106
        ('SrcId', 'uint8'),
        ('reserved', 'uint8'),
        ('ChanId', 'uint16'),

        ('Padding', 'int32', (32,)),
    ]
)

SlowChannelHeader = np.dtype(
    [
        ('Name', 'S32'),
        ('Channel', 'int32'),
        ('ADFreq', 'int32'),
        ('Gain', 'int32'),
        ('Enabled', 'int32'),
        ('PreampGain', 'int32'),
        # version 104
        ('SpikeChannel', 'int32'),
        # version 105
        ('Comment', 'S128'),
        # version 106
        ('SrcId', 'uint8'),
        ('reserved', 'uint8'),
        ('ChanId', 'uint16'),

        ('Padding', 'int32', (27,)),
    ]
)

DataBlockHeader = np.dtype(
    [
        ('Type', 'uint16'),
        ('UpperByteOf5ByteTimestamp', 'uint16'),
        ('TimeStamp', 'int32'),
        ('Channel', 'uint16'),
        ('Unit', 'uint16'),
        ('NumberOfWaveforms', 'uint16'),
        ('NumberOfWordsInWaveform', 'uint16'),
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

        self.dsp_channel_headers = None
        self.gain_per_dsp_channel = None
        self.dsp_frequency = None

        self.event_channel_headers = None
        self.event_frequency = None

        self.slow_channel_headers = None
        self.gain_per_slow_channel = None
        self.frequency_per_slow_channel = None

    def __enter__(self) -> Self:
        self.plx_stream = open(self.plx_file, 'br')
        self.global_header = self.consume_type(GlobalHeader)
        self.dsp_channel_headers = [
            self.consume_type(DspChannelHeader)
            for _ in range(self.global_header["NumDSPChannels"])
        ]
        self.gain_per_dsp_channel = self.get_gain_per_dsp_channel()
        self.dsp_frequency = self.global_header["WaveformFreq"]

        self.event_channel_headers = [
            self.consume_type(EventChannelHeader)
            for _ in range(self.global_header["NumEventChannels"])
        ]
        self.event_frequency = self.global_header["ADFrequency"]

        self.slow_channel_headers = [
            self.consume_type(SlowChannelHeader)
            for _ in range(self.global_header["NumSlowChannels"])
        ]
        self.gain_per_slow_channel = self.get_gain_per_slow_channel()
        self.frequency_per_slow_channel = self.get_frequency_per_slow_channel()

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

    def consume_type(self, dtype: np.dtype) -> dict[str, Any]:
        bytes = self.plx_stream.read(dtype.itemsize)
        if not bytes:
            return None

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

    def get_gain_per_slow_channel(self) -> dict[int, float]:
        gains = {}
        for header in self.slow_channel_headers:
            if self.global_header['Version'] in [100, 101]:
                gain = 5000. / (2048 * header['Gain'] * 1000.)
            elif self.global_header['Version'] in [102]:
                gain = 5000. / (2048 * header['Gain'] * header['PreampGain'])
            elif self.global_header['Version'] >= 103:
                gain = self.global_header['SlowMaxMagnitudeMV'] / (
                    .5 * (2 ** self.global_header['BitsPerSlowSample']) *
                    header['Gain'] * header['PreampGain'])
            gains[header['Channel']] = gain
        return gains

    def get_frequency_per_slow_channel(self) -> dict[int, float]:
        frequencies = {}
        for header in self.slow_channel_headers:
            frequencies[header['Channel']] = header['ADFreq']
        return frequencies

    def get_gain_per_dsp_channel(self) -> dict[int, float]:
        gains = {}
        for header in self.dsp_channel_headers:
            if self.global_header['Version'] < 103:
                gain = 3000. / (2048 * header['Gain'] * 1000.)
            elif 103 <= self.global_header['Version'] < 105:
                gain = self.global_header['SpikeMaxMagnitudeMV'] / (
                    .5 * 2. ** (self.global_header['BitsPerSpikeSample']) *
                    header['Gain'] * 1000.)
            elif self.global_header['Version'] >= 105:
                gain = self.global_header['SpikeMaxMagnitudeMV'] / (
                    .5 * 2. ** (self.global_header['BitsPerSpikeSample']) *
                    header['Gain'] * self.global_header['SpikePreAmpGain'])
            gains[header['Channel']] = gain
        return gains

    def next_block(self) -> dict[str, Any]:
        file_offset = self.plx_stream.tell()
        block_header = self.consume_type(DataBlockHeader)
        if not block_header:
            return None

        timestamp = block_header['UpperByteOf5ByteTimestamp'] * 2 ** 32 + block_header['TimeStamp']
        if block_header['Type'] == 4:
            # An event value with no payload.
            data = {
                "timestamp_seconds": timestamp / self.event_frequency,
                "value": block_header['Unit']
            }
        else:
            # A chunk of dsp or slow waveform data.
            shape = (block_header["NumberOfWaveforms"], block_header["NumberOfWordsInWaveform"])
            byte_count = shape[0] * shape[1] * 2
            bytes = self.plx_stream.read(byte_count)
            chunk = np.frombuffer(bytes, dtype='int16')
            chunk.reshape(shape)
            if block_header['Type'] == 1:
                # A dsp waveform.
                gain = self.gain_per_dsp_channel[block_header['Channel']]
                data = {
                    "timestamp_seconds": timestamp / self.dsp_frequency,
                    "frequency": self.dsp_frequency,
                    "waveforms": chunk * gain
                }
            elif block_header['Type'] == 5:
                # A slow waveform chunk.
                gain = self.gain_per_slow_channel[block_header['Channel']]
                frequency = self.frequency_per_slow_channel[block_header['Channel']]
                data = {
                    "timestamp_seconds": timestamp / frequency,
                    "frequency": frequency,
                    "waveforms": chunk * gain 
                }
            else:
                # This would be unexpected.
                data = None

        return {
            "file_offset": file_offset,
            "timestamp": timestamp,
            "type": block_header['Type'],
            "channel": block_header['Channel'],
            "unit": block_header['Unit'],
            "data": data
        }
