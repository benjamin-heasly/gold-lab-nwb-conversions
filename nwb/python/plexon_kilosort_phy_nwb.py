import sys
import logging
from typing import Optional, Sequence
from pathlib import Path
from argparse import ArgumentParser

import yaml

from plexon_reader import PlexonReader
from nwb_file import create, write
from plexon_sorting import add_plexon_sorting
from phy_sorting import add_phy_sorting
from kilosort_recording import add_kilosort_recording
from plexon_gold import add_lfps, add_eye_signals, add_recording_epochs, add_digital_events, add_trials


def run(
    experiment_file: Path,
    subject_file: Path,
    plx_file: Path,
    bin_file: Path,
    ops_file: Path,
    phy_dir: Path,
    nwb_out_file: Path,
    session_description: str = "",
    time_zone_name: str = "US/Eastern"
):
    """Write a new NWB file, combining data and config from several sources."""

    # Function to run a conversion, given args as used.
    with open(experiment_file, 'r') as f:
        experiment_info = yaml.safe_load(f)

    with open(subject_file, 'r') as f:
        subject_info = yaml.safe_load(f)

    # This is an expensive call.
    # It takes 1-10 minutes to parse and index the Plexon file block headers.
    # We try to do this once and reuse the same reader and its internal IO object as needed, below.
    plexon_reader = PlexonReader(plx_file=plx_file)
    session_start_time = plexon_reader.get_recording_datetime(zone_name=time_zone_name)
    session_id = Path(plx_file).stem
    print(f"Session {session_id} from {session_start_time}")

    nwb_file = create(
        experiment_info=experiment_info["experiment"],
        subject_info=subject_info["subject"],
        session_id=session_id,
        session_start_time=session_start_time,
        session_description=session_description
    )

    add_kilosort_recording(nwb_file, bin_file, ops_file)

    if phy_dir.exists():
        print(f"Adding sorting from Phy: {phy_dir.as_posix()}")
        add_phy_sorting(nwb_file, phy_dir)
    else:
        print(f"Adding sorting from Plexon: {plexon_reader.plexon_raw_io.filename}")
        add_plexon_sorting(nwb_file, plexon_reader.plexon_raw_io)

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

    write(nwb_file=nwb_file, file_path=nwb_out_file)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = ArgumentParser(description="Create a NWB file from Gold Lab config and data sources.")
    parser.add_argument("--experiment", "-e",
                        type=str,
                        help="name (in experiments-dir) or full path of your experiment's YAML file",
                        required=True
                        )
    parser.add_argument("--subject", "-s",
                        type=str,
                        help="name (in subjects-dir) or full path of your subject's YAML file",
                        required=True
                        )
    parser.add_argument("--session-id", "-i",
                        type=str,
                        help="unique name for your experiment session and/or .plx file (without the .plx)",
                        required=True
                        )
    parser.add_argument("--results-name", "-r",
                        type=str,
                        help="unique name for a processing/spike sorting attempt",
                        default="results")
    parser.add_argument("--session-description", "-d",
                        type=str,
                        help="any description to save along wiht this session",
                        default="")
    parser.add_argument("--data-dir",
                        type=str,
                        help="root directory with standard Gold Lab layout for exmeriment files",
                        default="~/data")
    parser.add_argument("--experiments-dir",
                        type=str,
                        help="directory to search by name for experiment YAML files",
                        default="./experiments")
    parser.add_argument("--subjects-dir",
                        type=str,
                        help="directory to search by name for subject YAML files",
                        default="./subjects")
    parser.add_argument("--plx-file",
                        type=str,
                        help="explicit/override path to Plexon .plx file to import",
                        default=None)
    parser.add_argument("--bin-file",
                        type=str,
                        help="explicit/override path to .bin file with raw neural waveform data",
                        default=None)
    parser.add_argument("--ops-file",
                        type=str,
                        help="explicit/override path to -ops.json file with probe and Kilosort metadata",
                        default=None)
    parser.add_argument("--phy-dir",
                        type=str,
                        help="explicit/override path to /phy folder with spike sorting results",
                        default=None)
    parser.add_argument("--nwb-out-file",
                        type=str,
                        help="explicit/override path for the NWB file to write out",
                        default=None)
    parser.add_argument("--time-zone-name",
                        type=str,
                        help="time zone to add to dates that are parsed from strings, if needed",
                        default="US/Eastern")

    cli_args = parser.parse_args(argv)

    experiment_file = Path(cli_args.experiment).expanduser()
    if not experiment_file.exists():
        experiment_file = Path(
            cli_args.experiments_dir,
            f"{cli_args.experiment}.yaml"
        )

    subject_file = Path(cli_args.subject).expanduser()
    if not subject_file.exists():
        subject_file = Path(
            cli_args.subjects_dir,
            f"{cli_args.subject}.yaml"
        )
    subject_dir_name = subject_file.stem

    if cli_args.plx_file:
        plx_file = Path(cli_args.plx_file).expanduser()
    else:
        plx_file = Path(
            cli_args.data_dir,
            subject_dir_name,
            "Raw",
            f"{cli_args.session_id}.plx"
        ).expanduser()

    if cli_args.bin_file:
        bin_file = Path(cli_args.bin_file).expanduser()
    else:
        bin_file = Path(
            cli_args.data_dir,
            subject_dir_name,
            "Kilosort",
            cli_args.session_id,
            f"{cli_args.session_id}.plx.bin"
        ).expanduser()

    if cli_args.ops_file:
        ops_file = Path(cli_args.ops_file).expanduser()
    else:
        ops_file = Path(
            cli_args.data_dir,
            subject_dir_name,
            "Kilosort",
            cli_args.session_id,
            f"{cli_args.session_id}-ops.json"
        ).expanduser()

    if cli_args.phy_dir:
        phy_dir = Path(cli_args.phy_dir).expanduser()
    else:
        phy_dir = Path(
            cli_args.data_dir,
            subject_dir_name,
            "Kilosort",
            cli_args.session_id,
            cli_args.results_name,
            "phy"
        ).expanduser()

    if cli_args.nwb_out_file:
        nwb_out_file = Path(cli_args.nwb_out_file).expanduser()
    else:
        nwb_out_file = Path(
            cli_args.data_dir,
            subject_dir_name,
            "NWB",
            f"{cli_args.session_id}-{cli_args.results_name}.nwb"
        ).expanduser()
    nwb_out_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        run(
            experiment_file,
            subject_file,
            plx_file,
            bin_file,
            ops_file,
            phy_dir,
            nwb_out_file,
            session_description=cli_args.session_description,
            time_zone_name=cli_args.time_zone_name
        )
        return 0
    except Exception:
        logging.exception("There was an error running this conversion!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
