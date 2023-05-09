from typing import Any
from datetime import datetime
from dateutil import tz

import numpy as np

from neo.rawio import PlexonRawIO


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
        """
        Transform an event channel_id to and event channel_indexe.
        Based on self.header['event_channels']
        channel_indexe is zero-based
        """
        event_channels = self.plexon_raw_io.header['event_channels']
        chan_ids = list(event_channels['id'])
        return chan_ids.index(channel_id)

    def read_events(self, channel_id):
        channel_index = self.event_channel_id_to_index(channel_id)
        print(f"channel_id {channel_id} has index {channel_index}")
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
