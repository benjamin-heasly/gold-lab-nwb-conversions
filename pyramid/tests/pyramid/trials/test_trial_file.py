from pathlib import Path
import json

import numpy as np

from pyramid.model.numeric_events import NumericEventList
from pyramid.trials.trials import Trial
from pyramid.trials.trial_file import TrialFileWriter


def test_no_writing(tmp_path):
    trial_file = Path(tmp_path, 'empty_trial_file.py').as_posix()
    with TrialFileWriter(trial_file) as writer:
        pass
    assert writer.file_stream is None

    with open(trial_file) as f:
        empty_trials = json.load(f)
    assert empty_trials == []


def test_write_empty(tmp_path):
    trial_file = Path(tmp_path, 'empty_trial_file.py').as_posix()
    with TrialFileWriter(trial_file) as writer:
        writer.append_trials([])
    assert writer.file_stream is None

    with open(trial_file) as f:
        empty_trials = json.load(f)
    assert empty_trials == []


sample_trials = [
    Trial(
        start_time=0,
        end_time=1.0,
        wrt_time=0.0,
        numeric_events={
            "foo": NumericEventList(np.array([[0.2, 0]])),
            "bar": NumericEventList(np.array([[0.1, 1]]))
        }
    ),
    Trial(
        start_time=1.0,
        end_time=2.0,
        wrt_time=1.5,
        numeric_events={
            "foo": NumericEventList(np.array([[1.2 - 1.5, 0], [1.3 - 1.5, 1]])),
            "bar": NumericEventList(np.empty([0, 2]))
        }
    ),
    Trial(
        start_time=2.0,
        end_time=3.0,
        wrt_time=2.5,
        numeric_events={
            "foo": NumericEventList(np.array([[2.2 - 2.5, 0], [2.3 - 2.5, 1]])),
            "bar": NumericEventList(np.empty([0, 2]))
        }
    ),
    Trial(
        start_time=3.0,
        end_time=None,
        wrt_time=3.5,
        numeric_events={
            "foo": NumericEventList(np.empty([0, 2])),
            "bar": NumericEventList(np.array([[3.1 - 3.5, 0]]))
        }
    )
]


def test_write_several_trials(tmp_path):
    trial_file = Path(tmp_path, 'trial_file.py').as_posix()
    with TrialFileWriter(trial_file) as writer:
        writer.append_trials(sample_trials)
    assert writer.file_stream is None

    with open(trial_file) as f:
        trials_interop = json.load(f)
        sample_trials_2 = [Trial.from_interop(trial_interop) for trial_interop in trials_interop]
    assert sample_trials_2 == sample_trials


def test_write_trials_incrementally(tmp_path):
    trial_file = Path(tmp_path, 'trial_file.py').as_posix()
    with TrialFileWriter(trial_file) as writer:
        for trial in sample_trials:
            writer.append_trials([trial])
    assert writer.file_stream is None

    with open(trial_file) as f:
        trials_interop = json.load(f)
        sample_trials_2 = [Trial.from_interop(trial_interop) for trial_interop in trials_interop]
    assert sample_trials_2 == sample_trials
