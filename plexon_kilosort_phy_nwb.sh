#!/bin/sh

set -e

python ./nwb/create_file.py
python ./nwb/add_kilosort_recording.py
python ./nwb/add_phy.py
python ./nwb/add_plexon_gold.py
