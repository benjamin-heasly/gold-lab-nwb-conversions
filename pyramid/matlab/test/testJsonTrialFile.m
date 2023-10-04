%% Empty trial file
emptyTrialFile = 'fixture_files/empty_trials.json';
trialFile = TrialFile(emptyTrialFile);
assert(isequal(class(trialFile.trialIterator), 'JsonTrialIterator'));
assert(isempty(trialFile.read()), 'Empty trial file should produce empty trial struct.');


%% Empty trial file with filter
emptyTrialFile = 'fixture_files/empty_trials.json';
trialFile = TrialFile(emptyTrialFile);
assert(isequal(class(trialFile.trialIterator), 'JsonTrialIterator'));
filterFun = @(trial) ~isempty(trial.enhancements);
assert(isempty(trialFile.read(filterFun)), 'Empty trial file should produce empty trial struct with filter.');


%% Sample Trial File
sampleTrialFile = 'fixture_files/sample_trials.json';
trialFile = TrialFile(sampleTrialFile);
assert(isequal(class(trialFile.trialIterator), 'JsonTrialIterator'));
expectedTrials = sampleTrials();
assert(isequal(trialFile.read(), expectedTrials), 'Sample trial file should produce expected trials.');


%% Sample Trial File with filter
sampleTrialFile = 'fixture_files/sample_trials.json';
trialFile = TrialFile(sampleTrialFile);
assert(isequal(class(trialFile.trialIterator), 'JsonTrialIterator'));
expectedTrials = sampleTrials();
filterFun = @(trial) ~isempty(trial.enhancements);
assert(isequal(trialFile.read(filterFun), expectedTrials(4:5)), 'Sample trial file should produce expected trials with filter.');
