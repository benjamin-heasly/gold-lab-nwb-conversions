%% Empty Trial File

% Set up to read a trial file with no data in it.
emptyTrialFile = 'fixture_files/empty_trials.hdf5';
hdf5TrialFile = Hdf5TrialFile(emptyTrialFile);

assert(isempty(hdf5TrialFile.readTrials()), 'Empty trial file should produce empty trial struct.');
assert(isempty(hdf5TrialFile.readTrials([1, 2, 3])), 'Empty trial file should produce empty trial struct for index selection.');


%% Sample Trial File

% Set up to read a trial file with data in it.
sampleTrialFile = 'fixture_files/sample_trials.hdf5';
hdf5TrialFile = Hdf5TrialFile(sampleTrialFile);

% Load up expected trial data as a Matlab struct array.
expectedTrials = sampleTrials();

assert(isequal(hdf5TrialFile.readTrials(), expectedTrials), 'Sample trial file should produce expected trials.');
assert(isequal(hdf5TrialFile.readTrials([1, 3, 4]), expectedTrials([1, 3, 4])), 'Sample trial file should produce expected trials for index selection.');
