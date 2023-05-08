from pynwb import NWBFile

from neuroconv.datainterfaces.ecephys.phy.phydatainterface import PhySortingInterface


def add_phy_sorting(
    nwb_file: NWBFile,
    phy_dir: str = "/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/phy",
    starting_time: float = 0.0
):
    """Add sorted clusters as seen by Phy to a working NWB file in memory.

    Phy data could come from Kilosort and/or other conversions like plx-to-phy.
    It seems like this one doesn't accept a starting_time.
    """

    print(f"Reading Phy data from dir: {phy_dir}")
    phy_interface = PhySortingInterface(folder_path=phy_dir)

    print(f"Adding Phy data to NWB file: {nwb_file}")
    phy_interface.run_conversion(nwbfile=nwb_file, metadata={}, overwrite=False)
