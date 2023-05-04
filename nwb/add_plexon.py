from datetime import datetime
from dateutil import tz

import numpy as np

from neo.rawio import PlexonRawIO
from pynwb import NWBHDF5IO

# This takes an existing NWB file and adds Plexon analog and digital word data.

# From args or defaults:
nwb_file = f"./cool_cool.nwb"
plx_file = "/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx"
update_session_start_time = True

# analog signal mappings for acquisition:
#   - channel names or ids for gaze x
#   - channel names or ids for gaze y
#   - channel names or ids for pupil
#   - channel names or ids for LFPs

# events for acquisition:
#   - channel names or ids for strobed words: time series per unique word
#   - channel names or ids for start and stop: recording epochs
#   - channel names or ids for others: time series per channel


class Drungus():
    def __init__(self, plx_file, block_index=0):
        self.block_index = block_index
        print(f"Starting reading block headers: {datetime.now()}")
        self.neo_reader = PlexonRawIO(filename=plx_file)
        self.neo_reader.parse_header()
        print(f"Finished reading block headers: {datetime.now()}")

    def get_recording_datetime(self, zone_name: str = "US/Eastern") -> datetime:
        if hasattr(self.neo_reader, "raw_annotations"):
            neo_metadata = self.neo_reader.raw_annotations["blocks"][self.block_index]

            if "rec_datetime" in neo_metadata:
                rec_datetime = neo_metadata["rec_datetime"]
                tzinfo = tz.gettz(zone_name)
                zoned_datetime = rec_datetime.replace(tzinfo=tzinfo)
                return zoned_datetime

        return None

    def describe_dingus(self):
        print("I have annotations.")
        self.neo_reader.print_annotations()

        signal_stream_count = self.neo_reader.signal_streams_count()
        print(f"I have {signal_stream_count} analog signal streams:")
        for stream in range(signal_stream_count):
            signal_channel_count = self.neo_reader.signal_channels_count(stream)
            print(f"  stream {stream} has {signal_channel_count} channels.")
            stream_id = self.neo_reader.header['signal_streams'][stream]['id']
            mask = self.neo_reader.header['signal_channels']['stream_id'] == stream_id
            signal_channels = self.neo_reader.header['signal_channels'][mask]
            for channel, info in enumerate(signal_channels):
                print(f"    stream {stream} channel {channel} info: {info}")

        event_channel_count = self.neo_reader.event_channels_count()
        print(f"I have {event_channel_count} event channels.")
        for channel in range(event_channel_count):
            info = self.neo_reader.header['event_channels'][channel]
            print(f"    channel {channel} info: {info}")

        block_count = self.neo_reader.block_count()
        print(f"I have {block_count} blocks:")
        for block in range(block_count):
            segment_count = self.neo_reader.segment_count(block)
            print(f"  block {block} has {segment_count} segments.")
            for segment in range(segment_count):
                segment_start = self.neo_reader.segment_t_start(block, segment)
                segment_end = self.neo_reader.segment_t_stop(block, segment)
                print(f"    segment {segment} goes from {segment_start} to {segment_end}.")

                for stream in range(signal_stream_count):
                    signal_channel_count = self.neo_reader.signal_channels_count(stream)
                    for channel in range(signal_channel_count):
                        chunk = self.neo_reader.get_analogsignal_chunk(
                            block_index=block,
                            seg_index=segment,
                            stream_index=stream,
                            channel_indexes=[channel]
                        )
                        scaled_chunk = self.neo_reader.rescale_signal_raw_to_float(
                            raw_signal=chunk,
                            stream_index=stream,
                            channel_indexes=[channel])
                        print(
                            f"      analog stream {stream} channel {channel} chunk of {len(scaled_chunk)}: {np.amin(scaled_chunk)} - {np.amax(scaled_chunk)}")

                for channel in range(event_channel_count):
                    event_count = self.neo_reader.event_count(block, segment, channel)
                    event_info = self.neo_reader.get_event_timestamps(block, segment, channel)
                    event_timestamps = event_info[0]
                    scaled_timestamps = self.neo_reader.rescale_event_timestamp(
                        event_timestamps=event_timestamps,
                        event_channel_index=channel)
                    if event_count:
                        print(
                            f"      event channel {channel} has {event_count} events: {np.amin(scaled_timestamps)} - {np.amax(scaled_timestamps)}")
                        print(f"      event channel {channel} labels: {event_info[1]}")
                        print(f"      event channel {channel} durations: {event_info[2]}")
                    else:
                        print(f"      event channel {channel} has {event_count} events.")


print(f"Reading Plexon data from: {plx_file}")
drungus = Drungus(plx_file=plx_file)
drungus.describe_dingus()

with NWBHDF5IO(nwb_file, mode="a") as io:
    nwb = io.read()

    # analog stuff to acquisition
    # event stuff to acquisition

    io.write(nwb)
