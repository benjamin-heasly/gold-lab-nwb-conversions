from neuroconv.datainterfaces.ecephys.phy.phydatainterface import PhySortingInterface

# This takes an existing NWB file and adds spike and cluster data from Phy.
# It expectes the a folder full of Phy files, such as Phy's params.py.

# From args or defaults:
nwb_file = f"./cool_cool.nwb"
phy_dir = "/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/phy"

# Phy data could come from Kilosort and/or other conversions like plx-to-phy.
print(f"Reading Phy data from dir: {phy_dir}")
phy_interface = PhySortingInterface(folder_path=phy_dir)

print(f"Adding Phy data to NWB file: {nwb_file}")
phy_interface.run_conversion(nwbfile_path=nwb_file, metadata={}, overwrite=False)
