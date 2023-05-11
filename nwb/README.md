# Neurodata Without Borders
Scripts and metadata for converting Plexon and other data files into [NWB](https://pynwb.readthedocs.io/en/stable/) files.

It also contains some README instructions for how to run this stuff.

This is a work in progress!

Tutorials I used when getting started.

 - https://pynwb.readthedocs.io/en/stable/tutorials/domain/ecephys.html
 - https://github.com/NeurodataWithoutBorders/nwb_tutorial/blob/main/HCK13/ecephys_tutorial.ipynb
 - https://pynwb.readthedocs.io/en/stable/tutorials/general/object_id.html#sphx-glr-tutorials-general-object-id-py
 - https://pynwb.readthedocs.io/en/stable/tutorials/general/read_basics.html#sphx-glr-tutorials-general-read-basics-py

This is one working example on Ben's laptop, using the gold lab folder conventions.
```
cd nwb
python python/plexon_kilosort_phy_nwb.py -e adpodr -s MrM -i MM_2022_11_28C_V-ProRec --data-dir /home/ninjaben/Desktop/codin/gold-lab/plexon_data

cd ..
jupyter notebook
# jupyter/nwb_panel.ipynb
# put in folder /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/NWB
# search
# choose MM_2022_11_28C_V-ProRec-results.nwb
# looks OK!
# PSTH for unit 41 seems to show trial-dependent activity of some sort
```

The Jyputer notebook and NWB widgets are beautiful when they work.
They also crash a lot from some data race conditions and need to be restarted.
Which is slow and irritating.

This is another working example using explicit paths instead of Gold Lab folder convention.
```
cd nwb
python python/plexon_kilosort_phy_nwb.py \
  -e adpodr \
  -s MrM \
  -i MM_2022_08_05_Rec-tentative-3units \
  --plx-file=/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx \
  --bin-file=/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/MM_2022_08_05_Rec-tentative-3units.plx.bin \
  --ops-file=/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/MM_2022_08_05_Rec-tentative-3units-ops.json \
  --phy-dir=/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/phy \
  --nwb-out-file=/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/NWB/MM_2022_08_05_Rec-tentative-3units.nwb

cd ..
jupyter notebook
# jupyter/nwb_panel.ipynb
# put in folder /home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/NWB
# search
# choose MM_2022_08_05_Rec-tentative-3units.nwb
# looks OK!
# PSTH for unit 3 sort of maybe shows trial-dependent activity
```
