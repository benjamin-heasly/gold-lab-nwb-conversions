# conda create --name nwb-poc python=3.11
# conda activate nwb-poc
# conda install -c conda-forge pynwb
# pip install neuroconv[plexon]
# pip install neuroconv[phy]
# pip install neo
# pip install spikeinterface[full,widgets]
# pip install probeinterface

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
        print(f"1: {datetime.now()}")
        self.neo_reader = PlexonRawIO(filename=plx_file)
        self.neo_reader.parse_header()
        print(f"2: {datetime.now()}")

    def get_recording_datetime(self, zone_name: str = "US/Eastern") -> datetime:
        if hasattr(self.neo_reader, "raw_annotations"):
            neo_metadata = self.neo_reader.raw_annotations["blocks"][self.block_index]

            if "rec_datetime" in neo_metadata:
                rec_datetime = neo_metadata["rec_datetime"]
                tzinfo = tz.gettz(zone_name)
                zoned_datetime = rec_datetime.replace(tzinfo=tzinfo)
                return zoned_datetime

        return None


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

# Extract waveforms from our plexon-converted-binary-plus-kilosort-ops.
recording_interface = ConvertedBinaryRecordingInterface(bin_file=bin_file, ops_file=ops_file)

# Extract original, manual Plexon sorting.
# This works, but is quite slow and a memory hog, so not good on the laptop.
# sorting_interface = PlexonSortingInterface(plx_file=plx_file)

# Extract converted or kilosort sorting from Phy.
phy_interface = PhySortingInterface(folder_path=phy_dir)

# Extract from Plexon AD channels
# Extract from Plexon DW channels
# Interpret Plexon DW channels as trials/blocks/correct/etc

# Export to NWB.
nwb_file = f"./{plx_name}.nwb"
print(f"Export to NWB {nwb_file}.")

converter = ConverterPipe(data_interfaces=[recording_interface, phy_interface])
metadata = converter.get_metadata()
metadata["NWBFile"].update(session_start_time=drungus.get_recording_datetime())
converter.run_conversion(nwbfile_path=nwb_file, metadata=metadata, overwrite=True)

# what a neo reader parsed header looks like
# thingy = {
#     'nb_block': 1, 'nb_segment': [1],
#     'signal_streams': array([('Signals 0', '0')],
#                             dtype=[('name', '<U64'),
#                                    ('id', '<U64')]),
#     'signal_channels':
#     array(
#         [('AD18', '17', 1000., 'int16', '', 0.0008138, 0., '0'),
#          ('AD48', '47', 1000., 'int16', '', 0.0012207, 0., '0'),
#          ('Pupil', '48', 1000., 'int16', '', 0.0012207, 0., '0'),
#          ('X\x0050', '49', 1000., 'int16', '', 0.0012207, 0., '0'),
#          ('Y\x0051', '50', 1000., 'int16', '', 0.0012207, 0., '0'),
#          ('AD52', '51', 1000., 'int16', '', 0.0012207, 0., '0')],
#         dtype=[('name', '<U64'),
#                ('id', '<U64'),
#                ('sampling_rate', '<f8'),
#                ('dtype', '<U16'),
#                ('units', '<U64'),
#                ('gain', '<f8'),
#                ('offset', '<f8'),
#                ('stream_id', '<U64')]),
#     'spike_channels':
#     array(
#         [('sig002', 'ch2#0', '', 4.57763672e-05, 0., -1, 0.),
#          ('sig002', 'ch2#1', '', 4.57763672e-05, 0., -1, 0.),
#          ('sig002', 'ch2#2', '', 4.57763672e-05, 0., -1, 0.),
#          ('sig002', 'ch2#3', '', 4.57763672e-05, 0., -1, 0.),
#          ('sig004', 'ch4#0', '', 4.57763672e-05, 0., -1, 0.)],
#         dtype=[('name', '<U64'),
#                ('id', '<U64'),
#                ('wf_units', '<U64'),
#                ('wf_gain', '<f8'),
#                ('wf_offset', '<f8'),
#                ('wf_left_sweep', '<i8'),
#                ('wf_sampling_rate', '<f8')]),
#     'event_channels':
#     array(
#         [('Event001', '1', b'event'),
#          ('Event002', '2', b'event'),
#          ('Event003', '3', b'event'),
#          ('Event004', '4', b'event'),
#          ('Event005', '5', b'event'),
#          ('Event006', '6', b'event'),
#          ('Event007', '7', b'event'),
#          ('Event008', '8', b'event'),
#          ('Event009', '9', b'event'),
#          ('Event010', '10', b'event'),
#          ('Event011', '11', b'event'),
#          ('Event012', '12', b'event'),
#          ('Event013', '13', b'event'),
#          ('Event014', '14', b'event'),
#          ('Event015', '15', b'event'),
#          ('Event016', '16', b'event'),
#          ('Strobed', '257', b'event'),
#          ('Start\x0018', '258', b'event'),
#          ('Stop\x00019', '259', b'event'),
#          ('Keyboard1', '101', b'event'),
#          ('Keyboard2', '102', b'event'),
#          ('Keyboard3', '103', b'event'),
#          ('Keyboard4', '104', b'event'),
#          ('Keyboard5', '105', b'event'),
#          ('Keyboard6', '106', b'event'),
#          ('Keyboard7', '107', b'event'),
#          ('Keyboard8', '108', b'event'),
#          ('Keyboard9', '109', b'event')],
#         dtype=[('name', '<U64'),
#                ('id', '<U64'),
#                ('type', 'S5')])}
