from typing import Any

from datetime import datetime
from dateutil import tz

import numpy as np

from neo.rawio import PlexonRawIO
from pynwb import NWBFile, NWBHDF5IO
from pynwb.ecephys import LFP, ElectricalSeries


class PlexonReader():
    def __init__(self, plx_file):
        self.plexon_raw_io = PlexonRawIO(filename=plx_file)

        # Header parsing is actually pretty slow, a few minutes.
        # We need to index the millions of data blocks that Plexon wrote out in no particular order.
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
                        print(
                            f"      event channel {channel} has {event_count} events: {np.amin(scaled_timestamps)} - {np.amax(scaled_timestamps)}")
                        print(f"      event channel {channel} labels: {event_info[1]}")
                        print(f"      event channel {channel} durations: {event_info[2]}")
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


def add_lfps(
        nwb_file: NWBFile,
        plexon_reader: PlexonReader,
        lfp_channel_ids: list[str],
        starting_time: float = 0.0
):
    """Add LFPs from the given Plexon analog channels to the working NWB file in memory."""

    print(f"Read channels to save as LFP: {lfp_channel_ids}")

    # Create a phony, bespoke device to represent Plexon LFP data.
    device = nwb_file.create_device(
        name="LFP device",
        description="Phony device for Plexon LFPs on analong channels",
        manufacturer="Plexon"
    )
    electrode_group = nwb_file.create_electrode_group(
        name="LFP electrode group",
        description="Phony electrode group for Plexon :LFPs on analong channels",
        device=device,
        location="unknown brain location",

    )

    # Set up standard electrode medadata "columns".
    # A previous step like add_kilosort_recording might have added these already.
    # TODO: the way add_kilosort_recording adds these is janky and obscure.
    # I'd prefer to set these up explicitly during the nwb_file.create(), so they match both places.
    if not nwb_file.electrodes or not "gain_to_uV" in nwb_file.electrodes.colnames:
        nwb_file.add_electrode_column(name='gain_to_uV', description="scale factor to apply to voltage data")
    if not nwb_file.electrodes or not "offset_to_uV" in nwb_file.electrodes.colnames:
        nwb_file.add_electrode_column(name='offset_to_uV', description="constant offset to apply to voltage data")
    if not nwb_file.electrodes or not "channel_name" in nwb_file.electrodes.colnames:
        nwb_file.add_electrode_column(name='channel_name', description="unique name to describe the channel")
    if not nwb_file.electrodes or not "rel_x" in nwb_file.electrodes.colnames:
        nwb_file.add_electrode_column(name='rel_x', description="x-position of the channel in its group")
    if not nwb_file.electrodes or not "rel_y" in nwb_file.electrodes.colnames:
        nwb_file.add_electrode_column(name='rel_y', description="y-position of the channel in its group")

    for channel_id in lfp_channel_ids:
        nwb_file.add_electrode(
            group=electrode_group,
            location="unknown brain location",
            channel_name=f"LFP on analog {channel_id}",
            gain_to_uV=1e6,
            offset_to_uV=0.0,
            rel_x=0.0,
            rel_y=0.0
        )
    electrode_region = nwb_file.create_electrode_table_region(
        region=list(range(len(lfp_channel_ids))),
        description="Phony LFP electrodes",
    )

    (lfp_analog_data, sample_rate) = plexon_reader.read_analog_channels(lfp_channel_ids)
    lfp_electrical_series = ElectricalSeries(
        name="ElectricalSeries",
        data=lfp_analog_data,
        electrodes=electrode_region,
        starting_time=starting_time,
        rate=sample_rate
    )

    lfp = LFP(electrical_series=lfp_electrical_series)
    ecephys_module = nwb_file.create_processing_module(
        name="ecephys",
        description="processed extracellular electrophysiology data"
    )
    ecephys_module.add(lfp)


# analog signal mappings for acquisition:
#   - channel names or ids for gaze x
#   - channel names or ids for gaze y
#   - channel names or ids for pupil
#   - channel names or ids for LFPs

# events for acquisition:
#   - channel names or ids for strobed words: time series per unique word
#   - channel names or ids for start and stop: recording epochs
#   - channel names or ids for others: time series per channel


# # create fake data with shape (50, 2)
# # the first dimension should always represent time, in seconds
# position_data = np.array([np.linspace(0, 10, 50),
#                           np.linspace(0, 8, 50)]).T
# position_timestamps = np.linspace(0, 50) / 200

# spatial_series_obj = SpatialSeries(
#     name='SpatialSeries',
#     description='(x,y) position in open field',
#     data=position_data,
#     timestamps=position_timestamps,
#     reference_frame='(0,0) is bottom left corner'
# )

# position_obj = Position(spatial_series=spatial_series_obj)

# behavior_module = nwbfile.create_processing_module(
#     name='behavior',
#     description='processed behavioral data'
# )
# behavior_module.add(position_obj)

# # Looks like the fake lfps have 10x the duration of the fake spie voltages.
# # So cool, they can be independent.
# # I like the mindset of just recording the facts.
# lfp_data = np.random.randn(fake_sample_count, electrode_counter)
# lfp_electrical_series = ElectricalSeries(
#     name="ElectricalSeries",
#     data=lfp_data,
#     electrodes=all_table_region,
#     starting_time=0.0,
#     rate=200.0,
# )

# lfp = LFP(electrical_series=lfp_electrical_series)

# # I think the "ecephys" name is arbitrary, but following a convention.
# ecephys_module = nwbfile.create_processing_module(
#     name="ecephys", description="processed extracellular electrophysiology data"
# )
# ecephys_module.add(lfp)
