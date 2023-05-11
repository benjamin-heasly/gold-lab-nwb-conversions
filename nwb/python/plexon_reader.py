from typing import Any
from datetime import datetime
from dateutil import tz

import numpy as np

from neo.rawio import PlexonRawIO


class PlexonReader():
    """Index a Plexon .plx file and its data blocks, so we can get at metadata and analog signals.
    
    Header parsing is actually pretty slow, something like 1-10 minutes for Gold Lab sessions.
    This is because .plx files have millions of small data blocks written out in unsorted order.
    Parsing all the block headers is worth the time because then we can seek to the block we want.
    """

    def __init__(self, plx_file):
        self.plexon_raw_io = PlexonRawIO(filename=plx_file)
        print(f"Start reading Plexon block headers: {datetime.now()}")
        self.plexon_raw_io.parse_header()
        print(f"Finished reading Plexon block headers: {datetime.now()}")

    def get_recording_datetime(self, zone_name: str = "US/Eastern") -> datetime:
        if hasattr(self.plexon_raw_io, "raw_annotations"):
            neo_metadata = self.plexon_raw_io.raw_annotations["blocks"][0]
            if "rec_datetime" in neo_metadata:
                rec_datetime = neo_metadata["rec_datetime"]
                tzinfo = tz.gettz(zone_name)
                zoned_datetime = rec_datetime.replace(tzinfo=tzinfo)
                return zoned_datetime
        return None

    def summarize(self):
        print("I have annotations.")
        self.plexon_raw_io.print_annotations()

        signal_stream_count = self.plexon_raw_io.signal_streams_count()
        print(f"I have {signal_stream_count} analog signal streams:")
        for stream in range(signal_stream_count):
            signal_channel_count = self.plexon_raw_io.signal_channels_count(stream)
            print(f"  stream {stream} has {signal_channel_count} channels.")
            stream_id = self.plexon_raw_io.header['signal_streams'][stream]['id']
            mask = self.plexon_raw_io.header['signal_channels']['stream_id'] == stream_id
            signal_channels = self.plexon_raw_io.header['signal_channels'][mask]
            for channel, info in enumerate(signal_channels):
                print(f"    stream {stream} channel {channel} info: {info}")

        event_channel_count = self.plexon_raw_io.event_channels_count()
        print(f"I have {event_channel_count} event channels.")
        for channel in range(event_channel_count):
            info = self.plexon_raw_io.header['event_channels'][channel]
            print(f"    channel {channel} info: {info}")

        block_count = self.plexon_raw_io.block_count()
        print(f"I have {block_count} blocks:")
        for block in range(block_count):
            segment_count = self.plexon_raw_io.segment_count(block)
            print(f"  block {block} has {segment_count} segments.")
            for segment in range(segment_count):
                segment_start = self.plexon_raw_io.segment_t_start(block, segment)
                segment_end = self.plexon_raw_io.segment_t_stop(block, segment)
                print(f"    segment {segment} goes from {segment_start} to {segment_end}.")

                for stream in range(signal_stream_count):
                    signal_channel_count = self.plexon_raw_io.signal_channels_count(stream)
                    for channel in range(signal_channel_count):
                        chunk = self.plexon_raw_io.get_analogsignal_chunk(
                            block_index=block,
                            seg_index=segment,
                            stream_index=stream,
                            channel_indexes=[channel]
                        )
                        scaled_chunk = self.plexon_raw_io.rescale_signal_raw_to_float(
                            raw_signal=chunk,
                            stream_index=stream,
                            channel_indexes=[channel])
                        print(
                            f"      analog stream {stream} channel {channel} chunk of {len(scaled_chunk)}: {np.amin(scaled_chunk)} - {np.amax(scaled_chunk)}")

                for channel in range(event_channel_count):
                    event_count = self.plexon_raw_io.event_count(block, segment, channel)
                    event_info = self.plexon_raw_io.get_event_timestamps(block, segment, channel)
                    event_timestamps = event_info[0]
                    scaled_timestamps = self.plexon_raw_io.rescale_event_timestamp(
                        event_timestamps=event_timestamps,
                        event_channel_index=channel)
                    if event_count:
                        print(f"      event channel {channel} has {event_count} events: {np.amin(scaled_timestamps)} - {np.amax(scaled_timestamps)}")
                        print(f"      event channel {channel} durations: {event_info[1]}")
                        print(f"      event channel {channel} labels: {event_info[2]}")
                    else:
                        print(f"      event channel {channel} has {event_count} events.")

    def read_analog_channels(self, channel_ids: list[Any], stream_index: int = 0) -> tuple[np.ndarray, float]:
        sample_rate = self.plexon_raw_io.get_signal_sampling_rate(stream_index)
        channel_indexes = self.plexon_raw_io.channel_id_to_index(stream_index=stream_index, channel_ids=channel_ids)
        block_count = self.plexon_raw_io.block_count()
        stream_data = []
        for block_index in range(block_count):
            block_data = []
            segment_count = self.plexon_raw_io.segment_count(block_index)
            for segment_index in range(segment_count):
                raw_chunk = self.plexon_raw_io.get_analogsignal_chunk(
                    block_index=block_index,
                    seg_index=segment_index,
                    stream_index=stream_index,
                    channel_indexes=channel_indexes
                )
                scaled_chunk = self.plexon_raw_io.rescale_signal_raw_to_float(
                    raw_signal=raw_chunk,
                    stream_index=stream_index,
                    channel_indexes=channel_indexes)
                block_data.append(scaled_chunk)
            stream_data.append(np.concatenate(block_data))
        analog_data = np.concatenate(stream_data)
        return (analog_data, sample_rate)

    def event_channel_id_to_index(self, channel_id):
        event_channels = self.plexon_raw_io.header['event_channels']
        chan_ids = list(event_channels['id'])
        return chan_ids.index(channel_id)

    def read_events(self, channel_id):
        channel_index = self.event_channel_id_to_index(channel_id)
        block_count = self.plexon_raw_io.block_count()
        channel_timestamps = []
        channel_durations = []
        channel_labels = []
        for block_index in range(block_count):
            block_timestamps = []
            block_durations = []
            block_labels = []
            segment_count = self.plexon_raw_io.segment_count(block_index)
            for segment_index in range(segment_count):
                (segment_timestamps, segment_durations, segment_labels) = self.plexon_raw_io.get_event_timestamps(
                    block_index,
                    segment_index,
                    channel_index
                )
                # Awkward test for truthiness:
                # Numpy arrays with one element act like that one element WRT truthiness.
                # So a numpy array with one timestamps that happens to be at zero, like array([0]), evaluates to False.
                # This is unlike a Python list with one zero element, like [0], which evalueates to True!
                # It seems dumb to me, like we're paying a price here for someone's unrelated use case.
                if segment_timestamps is not None and len(segment_timestamps):
                    scaled_segment_timestamps = self.plexon_raw_io.rescale_event_timestamp(
                        segment_timestamps,
                        event_channel_index=channel_index
                    )
                    block_timestamps.append(scaled_segment_timestamps)
                if segment_durations is not None and len(segment_durations):
                    block_durations.append(segment_durations)
                if segment_labels is not None and len(segment_labels):
                    block_labels.append(segment_labels)

            if block_timestamps:
                channel_timestamps.append(np.concatenate(block_timestamps))
            if block_durations:
                channel_durations.append(np.concatenate(block_durations))
            if block_labels:
                channel_labels.append(np.concatenate(block_labels))

        if channel_timestamps:
            timestamps = np.concatenate(channel_timestamps)
        else:
            timestamps = None

        if channel_durations:
            durations = np.concatenate(channel_durations)
        else:
            durations = None

        if channel_labels:
            labels = np.concatenate(channel_labels)
        else:
            labels = None

        return (timestamps, durations, labels)

# Here's some sample output from summarize()
# This was useful to see at one point, maybe it can be deleted now?
#
# Starting reading block headers: 2023-05-03 16:24:51.222327
# Finished reading block headers: 2023-05-03 16:26:17.957413
# I have annotations.
# Raw annotations
# *Block 0
#   -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#   -rec_datetime: 2022-08-05 12:02:30
#   -plexon_version: 107
#   *Segment 0
#     -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     -rec_datetime: 2022-08-05 12:02:30
#     -plexon_version: 107
#     *AnalogSignal 0
#       -name: Signals 0
#       -stream_id: 0
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#       -channel_names: [ AD18, AD48, Pupil, X50 ...
#       -channel_ids: [ 17, 47, 48, 49 ...
#     *Event/Epoch 0
#       -name: Event001
#       -id: 1
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 1
#       -name: Event002
#       -id: 2
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 2
#       -name: Event003
#       -id: 3
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 3
#       -name: Event004
#       -id: 4
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 4
#       -name: Event005
#       -id: 5
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 5
#       -name: Event006
#       -id: 6
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 6
#       -name: Event007
#       -id: 7
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 7
#       -name: Event008
#       -id: 8
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 8
#       -name: Event009
#       -id: 9
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 9
#       -name: Event010
#       -id: 10
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 10
#       -name: Event011
#       -id: 11
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 11
#       -name: Event012
#       -id: 12
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 12
#       -name: Event013
#       -id: 13
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 13
#       -name: Event014
#       -id: 14
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 14
#       -name: Event015
#       -id: 15
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 15
#       -name: Event016
#       -id: 16
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 16
#       -name: Strobed
#       -id: 257
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 17
#       -name: Start18
#       -id: 258
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 18
#       -name: Stop019
#       -id: 259
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 19
#       -name: Keyboard1
#       -id: 101
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 20
#       -name: Keyboard2
#       -id: 102
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 21
#       -name: Keyboard3
#       -id: 103
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 22
#       -name: Keyboard4
#       -id: 104
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 23
#       -name: Keyboard5
#       -id: 105
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 24
#       -name: Keyboard6
#       -id: 106
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 25
#       -name: Keyboard7
#       -id: 107
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 26
#       -name: Keyboard8
#       -id: 108
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *Event/Epoch 27
#       -name: Keyboard9
#       -id: 109
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *SpikeTrain 0
#       -name: sig002
#       -id: ch2#0
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *SpikeTrain 1
#       -name: sig002
#       -id: ch2#1
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *SpikeTrain 2
#       -name: sig002
#       -id: ch2#2
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *SpikeTrain 3
#       -name: sig002
#       -id: ch2#3
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx
#     *SpikeTrain 4
#       -name: sig004
#       -id: ch4#0
#       -file_origin: /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx

# I have 1 analog signal streams:
#   stream 0 has 6 channels.
#     stream 0 channel 0 info: ('AD18', '17', 1000., 'int16', '', 0.0008138, 0., '0')
#     stream 0 channel 1 info: ('AD48', '47', 1000., 'int16', '', 0.0012207, 0., '0')
#     stream 0 channel 2 info: ('Pupil', '48', 1000., 'int16', '', 0.0012207, 0., '0')
#     stream 0 channel 3 info: ('X\x0050', '49', 1000., 'int16', '', 0.0012207, 0., '0')
#     stream 0 channel 4 info: ('Y\x0051', '50', 1000., 'int16', '', 0.0012207, 0., '0')
#     stream 0 channel 5 info: ('AD52', '51', 1000., 'int16', '', 0.0012207, 0., '0')
# I have 28 event channels.
#     channel 0 info: ('Event001', '1', b'event')
#     channel 1 info: ('Event002', '2', b'event')
#     channel 2 info: ('Event003', '3', b'event')
#     channel 3 info: ('Event004', '4', b'event')
#     channel 4 info: ('Event005', '5', b'event')
#     channel 5 info: ('Event006', '6', b'event')
#     channel 6 info: ('Event007', '7', b'event')
#     channel 7 info: ('Event008', '8', b'event')
#     channel 8 info: ('Event009', '9', b'event')
#     channel 9 info: ('Event010', '10', b'event')
#     channel 10 info: ('Event011', '11', b'event')
#     channel 11 info: ('Event012', '12', b'event')
#     channel 12 info: ('Event013', '13', b'event')
#     channel 13 info: ('Event014', '14', b'event')
#     channel 14 info: ('Event015', '15', b'event')
#     channel 15 info: ('Event016', '16', b'event')
#     channel 16 info: ('Strobed', '257', b'event')
#     channel 17 info: ('Start\x0018', '258', b'event')
#     channel 18 info: ('Stop\x00019', '259', b'event')
#     channel 19 info: ('Keyboard1', '101', b'event')
#     channel 20 info: ('Keyboard2', '102', b'event')
#     channel 21 info: ('Keyboard3', '103', b'event')
#     channel 22 info: ('Keyboard4', '104', b'event')
#     channel 23 info: ('Keyboard5', '105', b'event')
#     channel 24 info: ('Keyboard6', '106', b'event')
#     channel 25 info: ('Keyboard7', '107', b'event')
#     channel 26 info: ('Keyboard8', '108', b'event')
#     channel 27 info: ('Keyboard9', '109', b'event')
# I have 1 blocks:
#   block 0 has 1 segments.
#     segment 0 goes from 0.0 to 3423.016.
#       analog stream 0 channel 0 chunk of 3423016: -0.4671224057674408 - 0.0447591133415699
#       analog stream 0 channel 1 chunk of 3423016: -0.08056640625 - 0.072021484375
#       analog stream 0 channel 2 chunk of 3423016: -2.49755859375 - 2.159423828125
#       analog stream 0 channel 3 chunk of 3423016: -2.49755859375 - 2.49755859375
#       analog stream 0 channel 4 chunk of 3423016: -2.49755859375 - 2.49755859375
#       analog stream 0 channel 5 chunk of 3423016: -0.120849609375 - 0.048828125
#       event channel 0 has 1 events: 0.00635 - 0.00635
#       event channel 0 labels: None
#       event channel 0 durations: ['0']
#       event channel 1 has 0 events.
#       event channel 2 has 0 events.
#       event channel 3 has 0 events.
#       event channel 4 has 0 events.
#       event channel 5 has 0 events.
#       event channel 6 has 0 events.
#       event channel 7 has 0 events.
#       event channel 8 has 0 events.
#       event channel 9 has 0 events.
#       event channel 10 has 0 events.
#       event channel 11 has 0 events.
#       event channel 12 has 0 events.
#       event channel 13 has 0 events.
#       event channel 14 has 0 events.
#       event channel 15 has 0 events.
#       event channel 16 has 40351 events: 0.0352 - 3422.630525
#       event channel 16 labels: None
#       event channel 16 durations: ['1007' '4919' '8036' ... '8195' '4904' '1000']
#       event channel 17 has 1 events: 0.0 - 0.0
#       event channel 17 labels: None
#       event channel 17 durations: ['0']
#       event channel 18 has 1 events: 3423.013875 - 3423.013875
#       event channel 18 labels: None
#       event channel 18 durations: ['0']
#       event channel 19 has 0 events.
#       event channel 20 has 0 events.
#       event channel 21 has 0 events.
#       event channel 22 has 0 events.
#       event channel 23 has 0 events.
#       event channel 24 has 0 events.
#       event channel 25 has 0 events.
#       event channel 26 has 0 events.
#       event channel 27 has 0 events.
