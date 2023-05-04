from datetime import datetime
from dateutil import tz

import spikeinterface.extractors as se
from neuroconv.datainterfaces.ecephys.basesortingextractorinterface import BaseSortingExtractorInterface

# This takes an existing NWB file and adds spike and cluster data from an original .plx file.

# From args or defaults:
nwb_file = f"./cool_cool.nwb"
plx_file = "/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx"
update_session_start_time = True

# This doesn't exist yet in neuroconv 0.24, but it might exist soon.
class PlexonSortingInterface(BaseSortingExtractorInterface):
    def Extractor(self, plx_file: str):
        sorting_extractor = se.read_plexon_sorting(file_path=plx_file)
        print(sorting_extractor)
        return sorting_extractor

    def __init__(self, plx_file: str, verbose: bool = True):
        super().__init__(plx_file=plx_file, verbose=verbose)

    def get_recording_datetime(self, zone_name: str = "US/Eastern") -> datetime:
        neo_reader = self.sorting_extractor.neo_reader

        if hasattr(neo_reader, "raw_annotations"):
            block_ind = self.sorting_extractor.block_index
            neo_metadata = neo_reader.raw_annotations["blocks"][block_ind]

            if "rec_datetime" in neo_metadata:
                # example: 2022-08-05 12:02:30
                rec_datetime = neo_metadata["rec_datetime"]
                tzinfo = tz.gettz(zone_name)
                zoned_datetime = rec_datetime.replace(tzinfo=tzinfo)
                return zoned_datetime

        return None

print(f"Reading Plexon sorting data from: {plx_file}")
sorting_interface = PlexonSortingInterface(plx_file=plx_file)
metadata = sorting_interface.get_metadata()

if update_session_start_time:
    session_start_time = sorting_interface.get_recording_datetime()
    if session_start_time:
        print(f"Updating session start time from .plx file: {session_start_time}")
        metadata["NWBFile"].update(session_start_time=session_start_time)

sorting_interface.run_conversion(nwbfile_path=nwb_file, metadata=metadata, overwrite=False)
