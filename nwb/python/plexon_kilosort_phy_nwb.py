from pathlib import Path
import yaml

from plexon_reader import PlexonReader
from nwb_file import create, write
from plexon_sorting import add_plexon_sorting
from phy_sorting import add_phy_sorting
from kilosort_recording import add_kilosort_recording
from plexon_gold import add_lfps, add_eye_signals, add_recording_epochs, add_digital_events, add_trials

# from args or defaults
experiment_file = "./nwb/experiments/adpodr.yaml"
subject_file = "./nwb/subjects/MrM.yaml"
extra_metadata = {"session_description": "A monkey doing interesting things."}
plx_file = "/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Sorted/MM_2022_08_05_Rec-tentative-3units.plx"
bin_file = "/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/MM_2022_08_05_Rec-tentative-3units.plx.bin"
ops_file = "/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/MM_2022_08_05_Rec-tentative-3units-ops.json"
phy_dir = "/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/SpikeInterface/phy"
nwb_out_path = "cool_cool.nwb"

with open(experiment_file, 'r') as f:
    experiment_info = yaml.safe_load(f)

with open(subject_file, 'r') as f:
    subject_info = yaml.safe_load(f)

# This is an expensive call.
# It takes 1-10 minutes to parse and index the Plexon file block headers.
# We try to do this once and reuse the same reader and its internal IO object as needed, below.
plexon_reader = PlexonReader(plx_file=plx_file)
session_start_time = plexon_reader.get_recording_datetime(zone_name="US/Eastern")
session_id = Path(plx_file).stem
print(f"Session {session_id} from {session_start_time}")

nwb_file = create(
    experiment_info=experiment_info["experiment"],
    subject_info=subject_info["subject"],
    session_id=session_id,
    session_start_time=session_start_time,
    extra_metadata=extra_metadata,
)

add_kilosort_recording(nwb_file, bin_file, ops_file)
add_plexon_sorting(nwb_file, plexon_reader.plexon_raw_io)
add_phy_sorting(nwb_file, phy_dir)

add_lfps(
    nwb_file,
    plexon_reader,
    lfp_channel_ids=experiment_info["plexon"]["lfp_channel_ids"]
)
add_eye_signals(
    nwb_file,
    plexon_reader,
    experiment_info["plexon"]["gaze_x_channel_id"],
    experiment_info["plexon"]["gaze_y_channel_id"],
    experiment_info["plexon"]["pupil_channel_id"]
)
add_recording_epochs(
    nwb_file,
    plexon_reader,
    experiment_info["plexon"]["start_channel_id"],
    experiment_info["plexon"]["stop_channel_id"]
)
add_digital_events(
    nwb_file,
    plexon_reader,
    experiment_info["plexon"]["strobe_channel_id"]
)
add_trials(
    nwb_file,
    experiment_info["plexon"]["trial_start_word"]
)

write(nwb_file=nwb_file, file_path=nwb_out_path)
