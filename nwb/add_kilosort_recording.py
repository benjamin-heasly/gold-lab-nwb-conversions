import json
import numpy as np

from pynwb import NWBHDF5IO
import spikeinterface as si
import probeinterface as pi
from neuroconv.datainterfaces.ecephys.baserecordingextractorinterface import BaseRecordingExtractorInterface

# This takes an existing NWB file and adds neural recording data.
# It expectes the a raw binary data file plus "ops" metadata, same as Kilosort.
# The ops should be JSON and must include ops.fs and ops.chanMap.

# From args or defaults:
nwb_file = f"./cool_cool.nwb"
bin_file = "/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/MM_2022_08_05_Rec-tentative-3units.plx.bin"
ops_file = "/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/MM_2022_08_05_Rec-tentative-3units-ops.json"
contact_shape="circle"
contact_radius=7.5


class KilosortBinaryRecordingInterface(BaseRecordingExtractorInterface):
    def Extractor(self, bin_file: str, ops_file: str, **kwargs):
        # Read the Kilosort ops to make a probe.
        with open(ops_file) as f:
            ops = json.load(f)

        probe = pi.Probe(ndim=2, si_units='um')
        connected_indices = np.where(ops["chanMap"]["connected"])[0]
        x_coords = np.array(ops["chanMap"]["xcoords"])[connected_indices]
        y_coords = np.array(ops["chanMap"]["ycoords"])[connected_indices]
        positions = np.vstack((x_coords, y_coords)).transpose()
        probe.set_contacts(positions, shapes=contact_shape, shape_params={'radius': contact_radius})
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

    def __init__(self, bin_file: str, ops_file: str, verbose: bool = True, es_key: str = "ElectricalSeries"):
        super().__init__(bin_file=bin_file, ops_file=ops_file, verbose=verbose, es_key=es_key)


print(f"Reading kilosort binary recording from bin file: {bin_file}")
print(f"Reading kilosort metadata from ops file: {ops_file}")
recording_interface = KilosortBinaryRecordingInterface(bin_file=bin_file, ops_file=ops_file)

print(f"Adding recording to NWB file: {nwb_file}")
recording_interface.run_conversion(nwbfile_path=nwb_file, overwrite=False)
