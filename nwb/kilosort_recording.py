import json
import numpy as np

from pynwb import NWBFile

import spikeinterface as si
import probeinterface as pi
from neuroconv.datainterfaces.ecephys.baserecordingextractorinterface import BaseRecordingExtractorInterface


class KilosortBinaryRecordingInterface(BaseRecordingExtractorInterface):
    def Extractor(self, bin_file: str, ops_file: str, contact_shape: str, contact_radius: float, **kwargs):
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

    def __init__(
            self,
            bin_file: str,
            ops_file: str,
            contact_shape: str = "circle",
            contact_radius: float = 7.5,
            verbose: bool = True,
            es_key: str = "ElectricalSeries"):
        super().__init__(
            bin_file=bin_file,
            ops_file=ops_file,
            contact_shape=contact_shape,
            contact_radius=contact_radius,
            verbose=verbose,
            es_key=es_key
        )


# TODO: this is doing something janky with nwb electrode table columns.
# We should be "allowed" to control this ourselves, ahead of time.
# That way we can match columns with our other "electrodes" like for LFPs. 
def add_kilosort_recording(
        nwb_file: NWBFile,
        bin_file: str,
        ops_file: str,
        starting_time: float = 0.0,
        contact_shape: str = "circle",
        contact_radius: float = 7.5):
    """ Add a binary recordig to an existing NWB file.
        The bin_file and ops_file are the same we'd pass to Kilosort.
        The ops file should be .json, not .mat
    """

    print(f"Reading kilosort binary recording from bin file: {bin_file}")
    print(f"Reading kilosort metadata from ops file: {ops_file}")
    recording_interface = KilosortBinaryRecordingInterface(
        bin_file=bin_file,
        ops_file=ops_file,
        contact_shape=contact_shape,
        contact_radius=contact_radius
    )

    print(f"Adding recording to NWB file: {nwb_file}")
    recording_interface.run_conversion(nwbfile=nwb_file, starting_time=starting_time, overwrite=False)
