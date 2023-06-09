from pynwb import NWBFile
from pynwb.behavior import EyeTracking, PupilTracking, SpatialSeries, TimeSeries
from pynwb.ecephys import LFP, ElectricalSeries

from plexon_reader import PlexonReader


def add_lfps(
    nwb_file: NWBFile,
    plexon_reader: PlexonReader,
    lfp_channel_ids: list[str],
    starting_time: float = 0.0
):
    """Add LFPs from the given Plexon analog channels to the working NWB file in memory."""

    print(f"Read channels to save as LFP: {lfp_channel_ids}")

    # Create a phony, bespoke device to represent Plexon LFP data.
    device = nwb_file.create_device(
        name="LFP device",
        description="Phony device for Plexon LFPs on analong channels",
        manufacturer="Plexon"
    )
    electrode_group = nwb_file.create_electrode_group(
        name="LFP electrode group",
        description="Phony electrode group for Plexon :LFPs on analong channels",
        device=device,
        location="unknown brain location",

    )

    # Set up standard electrode medadata "columns".
    # A previous step like add_kilosort_recording might have added these already.
    # TODO: the way add_kilosort_recording adds these is janky and obscure.
    # I'd prefer to set these up explicitly during the nwb_file.create(), so they match both places.
    if not nwb_file.electrodes or not "gain_to_uV" in nwb_file.electrodes.colnames:
        nwb_file.add_electrode_column(name='gain_to_uV', description="scale factor to apply to voltage data")
    if not nwb_file.electrodes or not "offset_to_uV" in nwb_file.electrodes.colnames:
        nwb_file.add_electrode_column(name='offset_to_uV', description="constant offset to apply to voltage data")
    if not nwb_file.electrodes or not "channel_name" in nwb_file.electrodes.colnames:
        nwb_file.add_electrode_column(name='channel_name', description="unique name to describe the channel")
    if not nwb_file.electrodes or not "rel_x" in nwb_file.electrodes.colnames:
        nwb_file.add_electrode_column(name='rel_x', description="x-position of the channel in its group")
    if not nwb_file.electrodes or not "rel_y" in nwb_file.electrodes.colnames:
        nwb_file.add_electrode_column(name='rel_y', description="y-position of the channel in its group")

    for channel_id in lfp_channel_ids:
        nwb_file.add_electrode(
            group=electrode_group,
            location="unknown brain location",
            channel_name=f"LFP on analog {channel_id}",
            gain_to_uV=1e6,
            offset_to_uV=0.0,
            rel_x=0.0,
            rel_y=0.0
        )
    electrode_region = nwb_file.create_electrode_table_region(
        region=list(range(len(lfp_channel_ids))),
        description="Phony LFP electrodes",
    )

    (lfp_analog_data, sample_rate) = plexon_reader.read_analog_channels(lfp_channel_ids)
    lfp_electrical_series = ElectricalSeries(
        name="ElectricalSeries",
        data=lfp_analog_data,
        electrodes=electrode_region,
        starting_time=starting_time,
        rate=sample_rate
    )

    lfp = LFP(electrical_series=lfp_electrical_series)
    ecephys_module = nwb_file.create_processing_module(
        name="ecephys",
        description="processed extracellular electrophysiology data"
    )
    ecephys_module.add(lfp)


def add_eye_signals(
    nwb_file: NWBFile,
    plexon_reader: PlexonReader,
    gaze_x_channel_id: str = None,
    gaze_y_channel_id: str = None,
    pupil_channel_id: str = None,
    starting_time: float = 0.0
):
    """Add gaze and pupil signals from the given Plexon analog channels to the working NWB file in memory."""

    if nwb_file.processing and "behavior" in nwb_file.processing:
        behavior_module = nwb_file.get_processing_module(name="behavior")
    else:
        behavior_module = nwb_file.create_processing_module(name="behavior", description="Processed behavioral data")

    if gaze_x_channel_id and gaze_y_channel_id:
        print(f"Read gaze_x_channel_id {gaze_x_channel_id}, gaze_y_channel_id {gaze_y_channel_id}")
        (gaze_analog_data, sample_rate) = plexon_reader.read_analog_channels([gaze_x_channel_id, gaze_y_channel_id])
        eye_position = SpatialSeries(
            name="eye_position",
            description="Eye position measured in degrees visual angle.",
            reference_frame="straight-ahead",
            unit="degrees",
            data=gaze_analog_data,
            starting_time=starting_time,
            rate=sample_rate,
        )
        eye_tracking = EyeTracking(name="EyeTracking", spatial_series=eye_position)
        behavior_module.add(eye_tracking)

    if pupil_channel_id:
        print(f"Read pupil_channel_id: {pupil_channel_id}")
        (pupil_analog_data, sample_rate) = plexon_reader.read_analog_channels([pupil_channel_id])
        pupil_diameter = TimeSeries(
            name="pupil_diameter",
            description="Pupil diameter extracted from the video of the eye.",
            unit="meters",
            data=pupil_analog_data,
            starting_time=starting_time,
            rate=sample_rate,
            continuity="continuous"
        )
        pupil_tracking = PupilTracking(time_series=pupil_diameter, name="PupilTracking")
        behavior_module.add(pupil_tracking)


def add_recording_epochs(
    nwb_file: NWBFile,
    plexon_reader: PlexonReader,
    start_channel_id: str,
    stop_channel_id: str,
    starting_time: float = 0.0
):
    """Add recording start-stop epochs from the given Plexon digital event channels to the working NWB file in memory."""

    print(f"Read recording epochs: start_channel_id {start_channel_id}, stop_channel_id {stop_channel_id}")
    (start_timestamps, _, _) = plexon_reader.read_events(start_channel_id)
    (stop_timestamps, _, _) = plexon_reader.read_events(stop_channel_id)
    for start, stop in zip(start_timestamps, stop_timestamps):
        nwb_file.add_epoch(
            start_time=start + starting_time,
            stop_time=stop + starting_time,
            tags=["plexon_recording_on"]
        )


def add_digital_events(
    nwb_file: NWBFile,
    plexon_reader: PlexonReader,
    strobe_channel_id: str,
    starting_time: float = 0.0
):
    """Add strobed words and timestamps from a Plexon digital event channel to the working NWB file in memory."""

    print(f"Read strobe words: strobe_channel_id {strobe_channel_id}")
    (strobe_timestamps, _, strobed_labels) = plexon_reader.read_events(strobe_channel_id)

    strobed_ints = [int(label) for label in strobed_labels]
    strobed_words = TimeSeries(
        name=f"strobed_words",
        description=f"Strobed word timestamps from Plexon event channel {strobe_channel_id}",
        timestamps=strobe_timestamps + starting_time,
        data=strobed_ints,
        unit="digital",
        continuity="instantaneous"
    )
    nwb_file.add_acquisition(strobed_words)


def add_trials(
    nwb_file: NWBFile,
    trial_start_word: int
):
    """Add trials in the working NWB file in memory based on the given strobed word (wip...)."""

    print(f"Mark trials based on strobed word {trial_start_word}")
    if not nwb_file.acquisition or not "strobed_words" in nwb_file.acquisition:
        print(f"Couldn't find 'strobed_words' time series in 'acquisition' container.")
        return

    strobed_words = nwb_file.get_acquisition("strobed_words")
    trial_word_indices = []
    for index, word in enumerate(strobed_words.data):
        if word == trial_start_word:
            trial_word_indices.append(index)
    trial_starts = strobed_words.timestamps[trial_word_indices]
    trial_count = len(trial_starts)
    print(f"Adding {trial_count} trials.")
    for index, trial_start in enumerate(trial_starts):
        next_index = index + 1
        if next_index >= trial_count:
            trial_end = strobed_words.timestamps[-1]
        else:
            trial_end = trial_starts[next_index]
        nwb_file.add_trial(
            start_time=trial_start,
            stop_time=trial_end
        )
