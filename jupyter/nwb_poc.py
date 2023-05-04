# conda create --name nwb-poc python=3.11
# conda activate nwb-poc
# conda install -c conda-forge pynwb


# https://pynwb.readthedocs.io/en/stable/tutorials/domain/ecephys.html
# https://github.com/NeurodataWithoutBorders/nwb_tutorial/blob/main/HCK13/ecephys_tutorial.ipynb
# https://pynwb.readthedocs.io/en/stable/tutorials/general/object_id.html#sphx-glr-tutorials-general-object-id-py
# https://pynwb.readthedocs.io/en/stable/tutorials/general/read_basics.html#sphx-glr-tutorials-general-read-basics-py


from datetime import datetime
from uuid import uuid4

import numpy as np
from dateutil.tz import tzlocal

from pynwb import NWBHDF5IO, NWBFile
from pynwb.ecephys import LFP, ElectricalSeries
from pynwb.file import Subject
from pynwb.behavior import SpatialSeries, Position


nwbfile = NWBFile(
    session_description="my first synthetic recording",
    identifier=str(uuid4()),
    session_start_time=datetime.now(tzlocal()),
    experimenter=[
        "Baggins, Bilbo",
    ],
    lab="Bag End Laboratory",
    institution="University of Anor at the Shire",
    experiment_description="I went on an adventure to reclaim vast treasures.",
    session_id="LONELYMTN001",
)

nwbfile.subject = Subject(
    subject_id='001',
    age='589', 
    description='gangle creature',
    species='Stoor', 
    sex='M'
)

# create fake data with shape (50, 2)
# the first dimension should always represent time, in seconds
position_data = np.array([np.linspace(0, 10, 50),
                          np.linspace(0, 8, 50)]).T
position_timestamps = np.linspace(0, 50) / 200

spatial_series_obj = SpatialSeries(
    name='SpatialSeries', 
    description='(x,y) position in open field',
    data=position_data,
    timestamps=position_timestamps,
    reference_frame='(0,0) is bottom left corner'
)

position_obj = Position(spatial_series=spatial_series_obj)

behavior_module = nwbfile.create_processing_module(
    name='behavior', 
    description='processed behavioral data'
)
behavior_module.add(position_obj)

# Here are the trials that the first tutorial mentioned, taken from the second!
nwbfile.add_trial_column(name='correct', description='whether the trial was correct')
nwbfile.add_trial(start_time=1.0, stop_time=5.0, correct=True)
nwbfile.add_trial(start_time=6.0, stop_time=10.0, correct=False)

trials_frame = nwbfile.trials.to_dataframe()
print(trials_frame)

device = nwbfile.create_device(
    name="array", description="my precious array", manufacturer="Aule Tech of Eregion"
)

# This "column" is a custom attribute for electrodes in general.
# We supply an attribute value for each electrode, below.
nwbfile.add_electrode_column(name="label", description="label of electrode")

nshanks = 4
nchannels_per_shank = 3
electrode_counter = 0

for ishank in range(nshanks):
    # create an electrode group for this shank
    electrode_group = nwbfile.create_electrode_group(
        name="shank{}".format(ishank),
        description="electrode group for shank {}".format(ishank),
        device=device,
        location="brain area",
    )
    # add electrodes to the electrode table
    for ielec in range(nchannels_per_shank):
        nwbfile.add_electrode(
            group=electrode_group,
            label="shank{}elec{}".format(ishank, ielec),
            location="brain area",
        )
        electrode_counter += 1

electrode_frame = nwbfile.electrodes.to_dataframe()
print(electrode_frame)

all_table_region = nwbfile.create_electrode_table_region(
    region=list(range(electrode_counter)),  # reference row indices 0 to N-1
    description="all electrodes",
)

fake_sample_count = 50
raw_data = np.random.randn(fake_sample_count, electrode_counter)
raw_electrical_series = ElectricalSeries(
    name="ElectricalSeries",
    data=raw_data,
    electrodes=all_table_region,
    starting_time=0.0,  # timestamp of the first sample in seconds relative to the session start time
    rate=20000.0,  # in Hz
)

nwbfile.add_acquisition(raw_electrical_series)

# Looks like the fake lfps have 10x the duration of the fake spie voltages.
# So cool, they can be independent.
# I like the mindset of just recording the facts.
lfp_data = np.random.randn(fake_sample_count, electrode_counter)
lfp_electrical_series = ElectricalSeries(
    name="ElectricalSeries",
    data=lfp_data,
    electrodes=all_table_region,
    starting_time=0.0,
    rate=200.0,
)

lfp = LFP(electrical_series=lfp_electrical_series)

# I think the "ecephys" name is arbitrary, but following a convention.
ecephys_module = nwbfile.create_processing_module(
    name="ecephys", description="processed extracellular electrophysiology data"
)
ecephys_module.add(lfp)

nwbfile.add_unit_column(name="quality", description="sorting quality")

poisson_lambda = 20
firing_rate = 20
n_units = 10
for n_units_per_shank in range(n_units):
    n_spikes = np.random.poisson(lam=poisson_lambda)
    spike_times = np.round(
        np.cumsum(np.random.exponential(1 / firing_rate, n_spikes)), 5
    )
    nwbfile.add_unit(
        spike_times=spike_times, quality="good", waveform_mean=[1.0, 2.0, 3.0, 4.0, 5.0]
    )

nwbfile.units.to_dataframe()

with NWBHDF5IO("ecephys_tutorial.nwb", "w") as io:
    io.write(nwbfile)

with NWBHDF5IO("ecephys_tutorial.nwb", "r") as io:
    read_nwbfile = io.read()
    print(read_nwbfile.acquisition["ElectricalSeries"])
    print(read_nwbfile.processing["ecephys"])
    print(read_nwbfile.processing["ecephys"]["LFP"])
    print(read_nwbfile.processing["ecephys"]["LFP"]["ElectricalSeries"])

    print(read_nwbfile.processing["ecephys"]["LFP"]["ElectricalSeries"].data[:])

    print("section of LFP:")
    print(read_nwbfile.processing["ecephys"]["LFP"]["ElectricalSeries"].data[:10, :3])
    print("")
    print("spike times from 0th unit:")
    print(read_nwbfile.units["spike_times"][0])

    for oid, obj in nwbfile.objects.items():
        print('%s/%s: %s "%s"' % (oid, obj.object_id, obj.neurodata_type, obj.name))

