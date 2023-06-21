import numpy as np

from pyramid.model.numeric_events import NumericEventList, NumericEventReader, NumericEventSource
from pyramid.trials.trials import Trial, TrialDelimiter, TrialExtractor


def test_trial_interop():
    start_time = 0
    end_time = 100
    wrt_time = 50
    trial = Trial(start_time, end_time, wrt_time)

    foo_events = NumericEventList(np.array([[t, 10*t] for t in range(100)]))
    trial.add_numeric_events("foo", foo_events)

    bar_events = NumericEventList(np.array([[t/10, 2*t] for t in range(1000)]))
    trial.add_numeric_events("bar", bar_events)

    empty_events = NumericEventList(np.empty([0, 2]))
    trial.add_numeric_events("empty", empty_events)

    interop = trial.to_interop()
    trial_2 = Trial.from_interop(interop)
    assert trial_2 == trial

    interop_2 = trial_2.to_interop()
    assert interop_2 == interop


class FakeNumericEventReader(NumericEventReader):

    def __init__(self, script=[[[0, 0]], [[1, 10]], [[2, 20]]]) -> None:
        self.index = -1
        self.script = script

    def read_next(self, timeout: float) -> NumericEventList:
        # Incrementing this index is like consuming a system or library resource:
        # - advance a file cursor
        # - increment past a file data block
        # - poll a network connection
        self.index += 1

        # Return dummy events from the contrived script, which might contain gaps and require retries.
        if timeout > 0 and self.index < len(self.script) and self.script[self.index]:
            return NumericEventList(np.array(self.script[self.index]))
        else:
            return None


def test_delimit_trials_from_separate_sources():
    start_reader = FakeNumericEventReader(script=[[[1, 1]], [[2, 1]], [[3, 1]]])
    start_source = NumericEventSource(start_reader)
    wrt_reader = FakeNumericEventReader(script=[[[1.5, 42]], [[2.5, 42]], [[2.6, 42]], [[3.5, 42]]])
    wrt_source = NumericEventSource(wrt_reader)
    delimiter = TrialDelimiter(start_source, 1, wrt_source, 42)

    # trial zero will be garbage, whatever happens before the first start event
    trial_zero = delimiter.read_next()
    assert len(trial_zero) == 1
    assert trial_zero[0] == Trial(0, 1.0, 0.0)

    # trials 1 and 2 will be well-formed
    trial_one = delimiter.read_next()
    assert len(trial_one) == 1
    assert trial_one[0] == Trial(1.0, 2.0, 1.5)

    trial_two = delimiter.read_next()
    assert len(trial_two) == 1
    assert trial_two[0] == Trial(2.0, 3.0, 2.5)

    # trial 3 will be made from whatever is left after the last start event
    assert not delimiter.read_next()
    trial_three = delimiter.read_last()
    assert trial_three == Trial(3.0, None, 3.5)


def test_delimiting_trials_from_combined_source():
    combined_reader = FakeNumericEventReader(
        script=[
            [[1, 1]],
            [[1.5, 42]],
            [[2, 1]],
            [[2.5, 42]],
            [[2.6, 42]],
            [[3, 1]],
            [[3.5, 42]]
        ]
    )
    combined_source = NumericEventSource(combined_reader)
    delimiter = TrialDelimiter(combined_source, 1, combined_source, 42)

    # Results will be same as in test_delimiting_trials_separate_sources.
    # But we'll need to poll the event source more often to see all the events.
    trial_zero = delimiter.read_next()
    assert len(trial_zero) == 1
    assert trial_zero[0] == Trial(0, 1.0, 0.0)

    # trials 1 and 2 will be well-formed
    assert not delimiter.read_next()
    trial_one = delimiter.read_next()
    assert len(trial_one) == 1
    assert trial_one[0] == Trial(1.0, 2.0, 1.5)

    assert not delimiter.read_next()
    assert not delimiter.read_next()
    trial_two = delimiter.read_next()
    assert len(trial_two) == 1
    assert trial_two[0] == Trial(2.0, 3.0, 2.5)

    # trial 3 will be made from whatever is left after the last start event
    assert not delimiter.read_next()
    trial_three = delimiter.read_last()
    assert trial_three == Trial(3.0, None, 3.5)


def test_delimit_multiple_trials_per_read():
    combined_reader = FakeNumericEventReader(
        script=[
            [[1, 1]],
            [[1.5, 42]],
            [[2, 1], [2.5, 42], [2.6, 42], [3, 1], [3.5, 42]]
        ]
    )
    combined_source = NumericEventSource(combined_reader)
    delimiter = TrialDelimiter(combined_source, 1, combined_source, 42)

    # Results will be same as in test_delimiting_trials_separate_sources.
    # But trials one and two will arrive together in the same read.
    trial_zero = delimiter.read_next()
    assert len(trial_zero) == 1
    assert trial_zero[0] == Trial(0, 1.0, 0.0)

    # trials 1 and 2 will be well-formed
    assert not delimiter.read_next()
    trials_one_and_2 = delimiter.read_next()
    assert len(trials_one_and_2) == 2
    assert trials_one_and_2[0] == Trial(1.0, 2.0, 1.5)
    assert trials_one_and_2[1] == Trial(2.0, 3.0, 2.5)

    # trial 3 will be made from whatever is left after the last start event
    assert not delimiter.read_next()
    trial_three = delimiter.read_last()
    assert trial_three == Trial(3.0, None, 3.5)


def test_extract_trials_with_data():
    # Delimit trials with start and wrt events.
    start_reader = FakeNumericEventReader(script=[[[1, 1]], [[2, 1]], [[3, 1]]])
    start_source = NumericEventSource(start_reader)
    wrt_reader = FakeNumericEventReader(script=[[[1.5, 42]], [[2.5, 42]], [[2.6, 42]], [[3.5, 42]]])
    wrt_source = NumericEventSource(wrt_reader)
    delimiter = TrialDelimiter(start_source, 1, wrt_source, 42)

    # Extract trials enriched with various other events.
    foo_reader = FakeNumericEventReader(script=[[[0.2, 0]], [[1.2, 0], [1.3, 1]], [[2.2, 0], [2.3, 1]]])
    foo_source = NumericEventSource(foo_reader)
    bar_reader = FakeNumericEventReader(script=[[[0.1, 1]], [[3.1, 0]]])
    bar_source = NumericEventSource(bar_reader)
    extractor = TrialExtractor(
        delimiter=delimiter,
        numeric_sources={
            "foo": foo_source,
            "bar": bar_source
        }
    )

    # trial zero will be garbage, whatever happens before the first start event
    trial_zero = extractor.read_next()
    assert len(trial_zero) == 1
    assert trial_zero[0] == Trial(
        start_time=0,
        end_time=1.0,
        wrt_time=0.0,
        numeric_events={
            "foo": NumericEventList(np.array([[0.2, 0]])),
            "bar": NumericEventList(np.array([[0.1, 1]]))
        }
    )

    # trials 1 and 2 will be well-formed
    trial_one = extractor.read_next()
    assert len(trial_one) == 1
    assert trial_one[0] == Trial(
        start_time=1.0,
        end_time=2.0,
        wrt_time=1.5,
        numeric_events={
            "foo": NumericEventList(np.array([[1.2 - 1.5, 0], [1.3 - 1.5, 1]])),
            "bar": NumericEventList(np.empty([0, 2]))
        }
    )

    trial_two = extractor.read_next()
    assert len(trial_two) == 1
    assert trial_two[0] == Trial(
        start_time=2.0,
        end_time=3.0,
        wrt_time=2.5,
        numeric_events={
            "foo": NumericEventList(np.array([[2.2 - 2.5, 0], [2.3 - 2.5, 1]])),
            "bar": NumericEventList(np.empty([0, 2]))
        }
    )

    # trial 3 will be made from whatever is left after the last start event
    assert not extractor.read_next()
    trial_three = extractor.read_last()
    assert trial_three == Trial(
        start_time=3.0,
        end_time=None,
        wrt_time=3.5,
        numeric_events={
            "foo": NumericEventList(np.empty([0, 2])),
            "bar": NumericEventList(np.array([[3.1 - 3.5, 0]]))
        }
    )

    # Event sources should discard old data after each trial is extracted.
    assert start_source.start_time() >= trial_three.start_time
    assert wrt_source.start_time() >= trial_three.start_time
    assert foo_source.event_list.get_times().size == 0
    assert bar_source.start_time() >= trial_three.start_time


def test_extract_multiple_trials_per_read():
    combined_reader = FakeNumericEventReader(
        script=[
            [[1, 1]],
            [[1.5, 42]],
            [[2, 1], [2.5, 42], [2.6, 42], [3, 1], [3.5, 42]]
        ]
    )
    combined_source = NumericEventSource(combined_reader)
    delimiter = TrialDelimiter(combined_source, 1, combined_source, 42)

    # Extract trials enriched with various other events.
    foo_reader = FakeNumericEventReader(script=[[[0.2, 0]], [[1.2, 0], [1.3, 1]], [[2.2, 0], [2.3, 1]]])
    foo_source = NumericEventSource(foo_reader)
    bar_reader = FakeNumericEventReader(script=[[[0.1, 1]], [[3.1, 0]]])
    bar_source = NumericEventSource(bar_reader)
    extractor = TrialExtractor(
        delimiter=delimiter,
        numeric_sources={
            "foo": foo_source,
            "bar": bar_source
        }
    )

    # Results will be same as in test_extract_trials_with_data.
    # But trials one and two will arrive together in the same read.
    # trial zero will be garbage, whatever happens before the first start event
    trial_zero = extractor.read_next()
    assert len(trial_zero) == 1
    assert trial_zero[0] == Trial(
        start_time=0,
        end_time=1.0,
        wrt_time=0.0,
        numeric_events={
            "foo": NumericEventList(np.array([[0.2, 0]])),
            "bar": NumericEventList(np.array([[0.1, 1]]))
        }
    )

    # trials one and two will arrive in the same read and be well-formed
    assert not extractor.read_next()
    trials_one_and_two = extractor.read_next()
    assert len(trials_one_and_two) == 2
    assert trials_one_and_two[0] == Trial(
        start_time=1.0,
        end_time=2.0,
        wrt_time=1.5,
        numeric_events={
            "foo": NumericEventList(np.array([[1.2 - 1.5, 0], [1.3 - 1.5, 1]])),
            "bar": NumericEventList(np.empty([0, 2]))
        }
    )
    assert trials_one_and_two[1] == Trial(
        start_time=2.0,
        end_time=3.0,
        wrt_time=2.5,
        numeric_events={
            "foo": NumericEventList(np.array([[2.2 - 2.5, 0], [2.3 - 2.5, 1]])),
            "bar": NumericEventList(np.empty([0, 2]))
        }
    )

    # trial 3 will be made from whatever is left after the last start event
    assert not extractor.read_next()
    trial_three = extractor.read_last()
    assert trial_three == Trial(
        start_time=3.0,
        end_time=None,
        wrt_time=3.5,
        numeric_events={
            "foo": NumericEventList(np.empty([0, 2])),
            "bar": NumericEventList(np.array([[3.1 - 3.5, 0]]))
        }
    )

    # Event sources should discard old data after each trial is extracted.
    assert combined_source.start_time() >= trial_three.start_time
    assert foo_source.event_list.get_times().size == 0
    assert bar_source.start_time() >= trial_three.start_time
