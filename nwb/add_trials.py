# processing: “ecephys”, “behavior”, or “misc”.

# This takes an existing NWB file and interprets raw strobed words time series as trials.
# This incorporates lab-specific knowledge about the experiment and the rig.

# strobed work mappings for processing:
#   - word whose timeline corresponds to "trial"
#   - words corresponding to correct and incorrect
#   - other FIRA/SPM stuff

# # Here are the trials that the first tutorial mentioned, taken from the second!
# nwbfile.add_trial_column(name='correct', description='whether the trial was correct')
# nwbfile.add_trial(start_time=1.0, stop_time=5.0, correct=True)
# nwbfile.add_trial(start_time=6.0, stop_time=10.0, correct=False)

# trials_frame = nwbfile.trials.to_dataframe()
# print(trials_frame)
