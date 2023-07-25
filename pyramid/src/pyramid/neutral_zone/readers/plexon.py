import logging
from types import TracebackType
from typing import ContextManager, Self, Any

import numpy as np
from pyramid.model.model import BufferData

from pyramid.model.events import NumericEventList
from pyramid.model.signals import SignalChunk
from pyramid.neutral_zone.readers.readers import Reader


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


class PlexonPlxRawReader(ContextManager):
    """Read a Pleoxn .plx file sequentially, block by block.

    This borrows from the python-neo project's PlexonRawIO.
    https://github.com/NeuralEnsemble/python-neo/blob/master/neo/rawio/plexonrawio.py

    The reason we don't just use PlexonRawIO here is we want to move through the file sequentially,
    block by block, over time. PlexonRawIO takes a different approach of indexing the whole file
    ahead of time and presenting a view per data type and channel, rather than sequentially.

    Thanks to the neo author Samuel Garcia for implementing a .plx file model in pure Python!
    """

    def __init__(self, plx_file: str) -> None:
        self.plx_file = plx_file

        self.plx_stream = None
        self.block_count = 0
        self.global_header = None

        self.dsp_channel_headers = None
        self.gain_per_dsp_channel = None
        self.dsp_frequency = None
        self.timestamp_frequency = None

        self.event_channel_headers = None

        self.slow_channel_headers = None
        self.gain_per_slow_channel = None
        self.frequency_per_slow_channel = None

    def __enter__(self) -> Self:
        self.plx_stream = open(self.plx_file, 'br')

        self.global_header = self.consume_type_as_dict(GlobalHeader)

        # DSP aka "spike" aka "waveform" channel configuration.
        self.dsp_channel_headers = [
            self.consume_type_as_dict(DspChannelHeader)
            for _ in range(self.global_header["NumDSPChannels"])
        ]
        self.gain_per_dsp_channel = self.get_gain_per_dsp_channel()
        self.dsp_frequency = self.global_header["WaveformFreq"]
        self.timestamp_frequency = self.global_header["ADFrequency"]

        # Event channel configuration.
        self.event_channel_headers = [
            self.consume_type_as_dict(EventChannelHeader)
            for _ in range(self.global_header["NumEventChannels"])
        ]

        # Slow, aka "ad", aka "analog" channel configuration.
        self.slow_channel_headers = [
            self.consume_type_as_dict(SlowChannelHeader)
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

    def consume_type(self, dtype: np.dtype) -> np.ndarray:
        # Consume part of the file, using the given dtype to choose the data size and format.
        bytes = self.plx_stream.read(dtype.itemsize)
        if not bytes:
            return None
        return np.frombuffer(bytes, dtype)[0]

    def consume_type_as_dict(self, dtype: np.dtype) -> dict[str, Any]:
        item = self.consume_type(dtype)
        if item is None:  # pragma: no cover
            return None

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
            # We don't currently have test files at versions < 103
            if self.global_header['Version'] in [100, 101]:  # pragma: no cover
                gain = 5000. / (2048 * header['Gain'] * 1000.)
            elif self.global_header['Version'] in [102]:  # pragma: no cover
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
            # We don't currently have test files at versions < 103
            if self.global_header['Version'] < 103:  # pragma: no cover
                gain = 3000. / (2048 * header['Gain'] * 1000.)
            elif 103 <= self.global_header['Version'] < 105:  # pragma: no cover
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
        # Consume the next block header and any waveform data.
        block_header = self.consume_type(DataBlockHeader)
        if not block_header:
            return None

        self.block_count += 1

        file_offset = self.plx_stream.tell()
        timestamp = block_header['UpperByteOf5ByteTimestamp'] * 2 ** 32 + block_header['TimeStamp']
        block_type = block_header['Type']
        if block_type == 4:
            # An event value with no waveform payload.
            return self.block_event_data(block_header, block_type, timestamp, file_offset)
        elif block_type == 1:
            # A spike event with a waveform payload.
            return self.block_dsp_data(block_header, block_type, timestamp, file_offset)
        elif block_type == 5:
            # A slow channel update with a waveform payload.
            return self.block_slow_data(block_header, block_type, timestamp, file_offset)
        else:  # pragma: no cover
            logging.warning(f"Skipping block of unknown type {block_type}.  Block header is: {block_header}")
            return None

    def block_event_data(
        self,
        block_header: np.ndarray,
        block_type: int,
        timestamp: float,
        file_offset: int
    ) -> dict[str, Any]:
        return {
            "type": block_type,
            "file_offset": file_offset,
            "timestamp": timestamp,
            "timestamp_seconds": timestamp / self.timestamp_frequency,
            "channel": block_header['Channel'],
            "unit": block_header['Unit'],
        }

    def consume_block_waveforms(self, block_header: np.ndarray) -> np.ndarray:
        shape = (block_header["NumberOfWaveforms"], block_header["NumberOfWordsInWaveform"])
        byte_count = shape[0] * shape[1] * 2
        bytes = self.plx_stream.read(byte_count)
        waveforms = np.frombuffer(bytes, dtype='int16')
        waveforms.reshape(shape)
        return waveforms

    def block_dsp_data(
        self,
        block_header: np.ndarray,
        block_type: int,
        timestamp: float,
        file_offset: int
    ) -> dict[str, Any]:
        waveforms = self.consume_block_waveforms(block_header)
        channel = block_header['Channel']
        gain = self.gain_per_dsp_channel[channel]
        return {
            "type": block_type,
            "file_offset": file_offset,
            "timestamp": timestamp,
            "timestamp_seconds": timestamp / self.timestamp_frequency,
            "channel": channel,
            "unit": block_header['Unit'],
            "frequency": self.dsp_frequency,
            "waveforms": waveforms * gain
        }

    def block_slow_data(
        self,
        block_header: np.ndarray,
        block_type: int,
        timestamp: float,
        file_offset: int
    ) -> dict[str, Any]:
        waveforms = self.consume_block_waveforms(block_header)
        channel = block_header['Channel']
        gain = self.gain_per_slow_channel[channel]
        channel_frequency = self.frequency_per_slow_channel[channel]
        return {
            "type": block_type,
            "file_offset": file_offset,
            "timestamp": timestamp,
            "timestamp_seconds": timestamp / self.timestamp_frequency,
            "channel": channel,
            "unit": block_header['Unit'],
            "frequency": channel_frequency,
            "waveforms": waveforms * gain
        }


class PlexonPlxReader(Reader):
    """Read plexon .plx ad waveform chunks, spike events, and other numeric events."""

    def __init__(
        self,
        plx_file: str = None,
        blocks_per_read: int = 500
    ) -> None:
        self.plx_file = plx_file
        self.raw_reader = PlexonPlxRawReader(plx_file)
        self.blocks_per_read = blocks_per_read

        self.spike_names = None
        self.event_names = None
        self.signal_names = None

    def __enter__(self) -> Any:
        self.raw_reader.__enter__()

        self.spike_names = {
            header["Channel"]: f"{header['Name']}_spikes"
            for header in self.raw_reader.dsp_channel_headers
        }
        self.event_names = {
            header["Channel"]: header["Name"]
            for header in self.raw_reader.event_channel_headers
        }
        self.signal_names = {
            header["Channel"]: header["Name"]
            for header in self.raw_reader.slow_channel_headers
        }

        return self

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None
    ) -> bool | None:
        return self.raw_reader.__exit__(__exc_type, __exc_value, __traceback)

    def read_next(self) -> dict[str, BufferData]:
        (name, data) = self.read_one_block()
        if name is None:
            # If there's nothing at all to read, the .plx file is done.
            raise StopIteration

        # Otherwise, return at least some results.
        results = {}
        results[name] = data
        block_count = 1
        while block_count < self.blocks_per_read and name is not None:
            (name, data) = self.read_one_block()
            block_count += 1

            if name in results:
                results[name].append(data)
            else:
                results[name] = data

        return results

    def read_one_block(self) -> tuple[str, BufferData]:
        block = self.raw_reader.next_block()
        if block is None:
            return (None, None)

        block_type = block['type']
        if block_type == 1:
            # Block has one spike event with timestamp, channel, and unit.
            return self.block_event(block)
        elif block_type == 4:
            # Block has one other event with timestamp, value.
            return self.block_spike_event(block)
        elif block_type == 5:
            # Block has a waveform signal chunk.
            return self.block_signal_chunk(block)
        else:  # pragma: no cover
            logging.warning(f"Ignoring block of unknown type {block_type}.")
            return (None, None)

    def block_event(self, block: dict[str, Any]) -> tuple[str, BufferData]:
        channel = block['channel']
        event_list = NumericEventList(np.array([[block['timestamp_seconds'], channel, block['unit']]]))
        return (self.spike_names[channel], event_list)

    def block_spike_event(self, block: dict[str, Any]) -> tuple[str, BufferData]:
        event_list = NumericEventList(np.array([[block['timestamp_seconds'], block['unit']]]))
        return (self.event_names[block['channel']], event_list)

    def block_signal_chunk(self, block: dict[str, Any]) -> tuple[str, BufferData]:
        channel = block['channel']
        signal_chunk = SignalChunk(
            sample_data=block['waveforms'].reshape([-1,1]),
            sample_frequency=float(block['frequency']),
            first_sample_time=float(block['timestamp_seconds']),
            channel_ids=[int(channel)]
        )
        return (self.signal_names[channel], signal_chunk)

    def get_initial(self) -> dict[str, BufferData]:
        # Peek at the .plx file so we can read headers -- but not consume data blocks yet.
        initial = {}
        with PlexonPlxRawReader(self.plx_file) as peek_reader:
            # Spike channels have numeric events like [timestamp, channel_id, unit_id]
            for header in peek_reader.dsp_channel_headers:
                initial[header['Name']] = NumericEventList(np.empty([0, 3], dtype='float64'))

            # Other event channels have numeric events like [timestamp, value]
            for header in peek_reader.event_channel_headers:
                name = header['Name']
                initial[name] = NumericEventList(np.empty([0, 2], dtype='float64'))

            # Slow ad channels have Signal chunks.
            for header in peek_reader.slow_channel_headers:
                name = header['Name']
                if name in initial:
                    name = f"{name}_signal"
                initial[name] = SignalChunk(
                    sample_data=np.empty([0, 1], dtype='float64'),
                    sample_frequency=float(header["ADFreq"]),
                    first_sample_time=float(0.0),
                    channel_ids=[int(header["Channel"])]
                )

        return initial
