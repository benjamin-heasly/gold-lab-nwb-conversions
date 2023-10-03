%% Empty Trial File

% Set up to read a trial file with no data in it.
emptyTrialFile = 'fixture_files/empty_trials.json';
jsonTrialFile = JsonTrialFile(emptyTrialFile);

assert(isempty(jsonTrialFile.readTrials()), 'Empty trial file should produce empty trial struct.');
assert(isempty(jsonTrialFile.readTrials([1, 2, 3])), 'Empty trial file should produce empty trial struct for index selection.');


%% Sample Trial File

% Set up to read a trial file with data in it.
sampleTrialFile = 'fixture_files/sample_trials.json';
jsonTrialFile = JsonTrialFile(sampleTrialFile);

% Load up expected trial data as a Matlab struct array.
expectedTrials = sampleTrials();

assert(isequal(jsonTrialFile.readTrials(), expectedTrials), 'Sample trial file should produce expected trials.');
assert(isequal(jsonTrialFile.readTrials([1, 3, 4]), expectedTrials([1, 3, 4])), 'Sample trial file should produce expected trials for index selection.');
