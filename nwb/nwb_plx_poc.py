# https://neuroconv.readthedocs.io/en/main/conversion_examples_gallery/recording/plexon.html


from datetime import datetime
from dateutil import tz
from pathlib import Path
import json

import numpy as np

import spikeinterface as si
import spikeinterface.extractors as se
import probeinterface as pi

from neo.rawio import PlexonRawIO

from neuroconv import ConverterPipe
from neuroconv.datainterfaces.ecephys.baserecordingextractorinterface import BaseRecordingExtractorInterface
from neuroconv.datainterfaces.ecephys.basesortingextractorinterface import BaseSortingExtractorInterface
from neuroconv.datainterfaces.ecephys.phy.phydatainterface import PhySortingInterface


class ConvertedBinaryRecordingInterface(BaseRecordingExtractorInterface):
    def Extractor(self, bin_file: Path, ops_file: Path, **kwargs):
        # Read the kilosort ops to make a probe.
        print(f"Load ops {ops_file}")
        with open(ops_file) as f:
            ops = json.load(f)

        print("Make probe.")
        probe = pi.Probe(ndim=2, si_units='um')
        connected_indices = np.where(ops["chanMap"]["connected"])[0]
        x_coords = np.array(ops["chanMap"]["xcoords"])[connected_indices]
        y_coords = np.array(ops["chanMap"]["ycoords"])[connected_indices]
        positions = np.vstack((x_coords, y_coords)).transpose()
        probe.set_contacts(positions, shapes='circle', shape_params={'radius': 7.5})
        probe.set_device_channel_indices(list(range(0, connected_indices.size)))

        channel_ids = np.argsort(ops["chanMap"]["ycoords"])[connected_indices]
        probe.set_contact_ids(channel_ids)

        # Set up the binary waveform extractor with the probe.
        print(f"Extract from binary {bin_file}.")
        recording_extractor = si.core.BinaryRecordingExtractor(
            bin_file,
            sampling_frequency=float(ops['fs']),
            num_chan=int(ops["NchanTOT"]),
            dtype="int16",
            gain_to_uV=1,
            offset_to_uV=0,
            is_filtered=True,
            time_axis=0
        )
        recording_extractor = recording_extractor.set_probe(probe)
        print(recording_extractor)
        return recording_extractor

    def __init__(self, bin_file: Path, ops_file: Path, verbose: bool = True, es_key: str = "ElectricalSeries"):
        super().__init__(bin_file=bin_file, ops_file=ops_file, verbose=verbose, es_key=es_key)


class PlexonSortingInterface(BaseSortingExtractorInterface):
    def Extractor(self, plx_file: Path):
        print(f"Extract from plx {plx_file}.")
        sorting_extractor = se.read_plexon_sorting(file_path=plx_file)
        print(sorting_extractor)
        return sorting_extractor

    def __init__(self, plx_file: Path, verbose: bool = True):
        super().__init__(plx_file=plx_file, verbose=verbose)

    def get_recording_datetime(self, zone_name: str = "US/Eastern") -> datetime:
        neo_reader = self.sorting_extractor.neo_reader

        if hasattr(neo_reader, "raw_annotations"):
            block_ind = self.sorting_extractor.block_index
            neo_metadata = neo_reader.raw_annotations["blocks"][block_ind]

            if "rec_datetime" in neo_metadata:
                # example: 2022-08-05 12:02:30
                rec_datetime = neo_metadata["rec_datetime"]
                print(f"Plexon rec_datetime ({type(rec_datetime)}): {rec_datetime}")

                tzinfo = tz.gettz(zone_name)
                zoned_datetime = rec_datetime.replace(tzinfo=tzinfo)
                return zoned_datetime

        return None


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
                        print(f"      analog stream {stream} channel {channel} chunk of {len(scaled_chunk)}: {np.amin(scaled_chunk)} - {np.amax(scaled_chunk)}")

                for channel in range(event_channel_count):
                    event_count = self.neo_reader.event_count(block, segment, channel)
                    event_info = self.neo_reader.get_event_timestamps(block, segment, channel)
                    event_timestamps = event_info[0]
                    scaled_timestamps = self.neo_reader.rescale_event_timestamp(
                        event_timestamps=event_timestamps,
                        event_channel_index=channel)
                    if event_count:
                        print(f"      event channel {channel} has {event_count} events: {np.amin(scaled_timestamps)} - {np.amax(scaled_timestamps)}")
                        print(f"      event channel {channel} labels: {event_info[1]}")
                        print(f"      event channel {channel} durations: {event_info[2]}")
                    else:
                        print(f"      event channel {channel} has {event_count} events.")


# header read for this one is about 1 minute
plx_name = "MM_2022_08_05_Rec-tentative-3units"
plx_file = Path(f"/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/{plx_name}.plx")
bin_file = Path(f"/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/{plx_name}.plx.bin")
ops_file = Path(f"/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/{plx_name}-ops.json")
phy_dir = Path("/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/phy")

# header read for this one is like 10 minutes.
# It's doing significant indexing of data blocks -- scanning through the whole file -- is why it's slow.
# # plexonrawio.py at line 94, runs out of memory appending block header info across the whole file.
# I think making a numpy view() of memmapped data was effectively leaking the whole file into memory
# in addition to index info -- since the view() wants to be backed by the original buffer.
# Also the data blocks headers themselves are about a third of the file size, to begin with!
# lots of short spike waveforms, one per block.
# I hacked this up to do less caching during the read, seems to work OK now.
# Maybe PR all of this.
# https://github.com/NeuralEnsemble/python-neo
# I'm on neo 0.12, which seems to be the latest.
# So if the PR were accepted, I could maybe even pin to the next release and keep using spikeinterface!
# plx_name = "MM_2022_11_28C_V-ProRec"
# plx_file = Path(f"/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Raw/{plx_name}.plx")
# bin_file = Path(f"/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Kilosort/{plx_name}.plx.bin")
# ops_file = Path(f"/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Kilosort/{plx_name}-ops.json")
# phy_dir = Path(f"/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Kilosort/{plx_name}-results/phy")


# Ad-hoc access to plexon file?
drungus = Drungus(plx_file)
drungus.describe_dingus()

# Extract waveforms from our plexon-converted-binary-plus-kilosort-ops.
recording_interface = ConvertedBinaryRecordingInterface(bin_file=bin_file, ops_file=ops_file)

# Extract original, manual Plexon sorting.
# This works, but is quite slow and a memory hog, so not good on the laptop.
# sorting_interface = PlexonSortingInterface(plx_file=plx_file)

# Extract converted or kilosort sorting from Phy.
phy_interface = PhySortingInterface(folder_path=phy_dir)

# Extract from Plexon AD channels -- seem to be showing up as analog "signal channels"
# I think the gaze and pupil channels are covered here: https://github.com/NeurodataWithoutBorders/pynwb/blob/dev/src/pynwb/base.py#L76
# I think the LFP channels are covered here: https://github.com/NeurodataWithoutBorders/pynwb/blob/dev/src/pynwb/ecephys.py#L247

# Extract from Plexon DW channels -- apparently the digital words show up as "durations" on event channel index 16 / name 'Strobed' / id 257
# As far as I can tell, we'd make a series for each word, and record an "instantaneous" series for each: https://github.com/NeurodataWithoutBorders/pynwb/blob/dev/src/pynwb/base.py#L76

# Interpret Plexon DW channels as trials/blocks/correct/etc
# I think we'd use add_trial with custom fields like "correct".

# Export to NWB.
nwb_file = f"./{plx_name}.nwb"
print(f"Export to NWB {nwb_file}.")

converter = ConverterPipe(data_interfaces=[recording_interface, phy_interface])
metadata = converter.get_metadata()
metadata["NWBFile"].update(session_start_time=drungus.get_recording_datetime())
converter.run_conversion(nwbfile_path=nwb_file, metadata=metadata, overwrite=True)

# What some plexon/neo header and file data looks like, in summary:
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
