import numpy as np

from pyramid.model.numeric_events import NumericEventList, NumericEventBuffer
from pyramid.neutral_zone.readers.readers import Reader, ReaderRoute, ReaderRouter
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


class FakeNumericEventReader(Reader):

    def __init__(self, script=[]) -> None:
        self.index = -1
        self.script = script

    def read_next(self) -> dict[str, NumericEventList]:
        # Incrementing this index is like consuming a system or library resource:
        # - advance a file cursor
        # - increment past a file data block
        # - poll a network connection
        self.index += 1

        # Return dummy events from the contrived script, which might contain gaps and require retries.
        if self.index < len(self.script) and self.script[self.index]:
            return {
                "events": NumericEventList(np.array(self.script[self.index]))
            }
        else:
            return None


def test_delimit_trials_from_pivate_buffer():
    start_reader = FakeNumericEventReader(script=[[[1, 1010]], [[2, 1010]], [[3, 1010]]])
    start_buffer = NumericEventBuffer()
    start_route = ReaderRoute("events", "start")
    start_router = ReaderRouter(start_reader, {"start": start_buffer}, [start_route])

    delimiter = TrialDelimiter(start_buffer, 1010)

    # trial zero will be garbage, whatever happens before the first start event
    assert start_router.route_next() == True
    trial_zero = delimiter.next()
    assert len(trial_zero) == 1
    assert trial_zero[0] == Trial(0, 1.0)

    # trials 1 and 2 will be well-formed
    assert start_router.route_next() == True
    trial_one = delimiter.next()
    assert len(trial_one) == 1
    assert trial_one[0] == Trial(1.0, 2.0)

    assert start_router.route_next() == True
    trial_two = delimiter.next()
    assert len(trial_two) == 1
    assert trial_two[0] == Trial(2.0, 3.0)

    # trial 3 will be made from whatever is left after the last start event
    assert start_router.route_next() == False
    assert not delimiter.next()
    trial_three = delimiter.last()
    assert trial_three == Trial(3.0, None)


def test_delimit_trials_from_shared_buffer():
    start_reader = FakeNumericEventReader(
        script=[
            [[0.5, 42]],
            [[1, 1010]],
            [[1.5, 42]],
            [[1.6, 42]],
            [[2, 1010]],
            [[2.5, 42]],
            [[3, 1010]],
            [[3.5, 42]],
        ]
    )
    start_buffer = NumericEventBuffer()
    start_route = ReaderRoute("events", "start")
    start_router = ReaderRouter(start_reader, {"start": start_buffer}, [start_route])

    delimiter = TrialDelimiter(start_buffer, 1010)

    # trial zero will be garbage, whatever happens before the first start event
    assert start_router.route_next() == True
    assert start_router.route_next() == True
    trial_zero = delimiter.next()
    assert len(trial_zero) == 1
    assert trial_zero[0] == Trial(0, 1.0)

    # trials 1 and 2 will be well-formed
    assert start_router.route_next() == True
    assert start_router.route_next() == True
    assert start_router.route_next() == True
    trial_one = delimiter.next()
    assert len(trial_one) == 1
    assert trial_one[0] == Trial(1.0, 2.0)

    assert start_router.route_next() == True
    assert start_router.route_next() == True
    trial_two = delimiter.next()
    assert len(trial_two) == 1
    assert trial_two[0] == Trial(2.0, 3.0)

    # trial 3 will be made from whatever is left after the last start event
    assert start_router.route_next() == True
    assert start_router.route_next() == False
    assert not delimiter.next()
    trial_three = delimiter.last()
    assert trial_three == Trial(3.0, None)


def test_delimit_multiple_trials_per_read():
    start_reader = FakeNumericEventReader(
        script=[
            [[1, 1010]],
            [[1.5, 42]],
            [[2, 1010], [2.5, 42], [2.6, 42], [3, 1010], [3.5, 42]]
        ]
    )
    start_buffer = NumericEventBuffer()
    start_route = ReaderRoute("events", "start")
    start_router = ReaderRouter(start_reader, {"start": start_buffer}, [start_route])

    delimiter = TrialDelimiter(start_buffer, 1010)

    # trial zero will be garbage, whatever happens before the first start event
    assert start_router.route_next() == True
    trial_zero = delimiter.next()
    assert len(trial_zero) == 1
    assert trial_zero[0] == Trial(0, 1.0)

    # trials 1 and 2 will be well-formed
    assert start_router.route_next() == True
    assert start_router.route_next() == True
    trials_one_and_two = delimiter.next()
    assert len(trials_one_and_two) == 2
    assert trials_one_and_two[0] == Trial(1.0, 2.0)
    assert trials_one_and_two[1] == Trial(2.0, 3.0)

    # trial 3 will be made from whatever is left after the last start event
    assert start_router.route_next() == False
    assert not delimiter.next()
    trial_three = delimiter.last()
    assert trial_three == Trial(3.0, None)


def test_populate_trials_from_private_buffers():
    # Expect trials starting at times 0, 1, 2, and 3.
    start_reader = FakeNumericEventReader(script=[[[1, 1010]], [[2, 1010]], [[3, 1010]]])
    start_buffer = NumericEventBuffer()
    start_route = ReaderRoute("events", "start")
    start_router = ReaderRouter(start_reader, {"start": start_buffer}, [start_route])

    delimiter = TrialDelimiter(start_buffer, 1010)

    # Expect wrt times half way through trials 1, 2, and 3.
    wrt_reader = FakeNumericEventReader(script=[[[1.5, 42]], [[2.5, 42], [2.6, 42]], [[3.5, 42]]])
    wrt_buffer = NumericEventBuffer()
    wrt_route = ReaderRoute("events", "wrt")
    wrt_router = ReaderRouter(wrt_reader, {"wrt": wrt_buffer}, [wrt_route])

    # Expect "foo" events in trials 0, 1, and 2, before the wrt times.
    foo_reader = FakeNumericEventReader(script=[[[0.2, 0]], [[1.2, 0], [1.3, 1]], [[2.2, 0], [2.3, 1]]])
    foo_buffer = NumericEventBuffer()
    foo_route = ReaderRoute("events", "foo")
    foo_router = ReaderRouter(foo_reader, {"foo": foo_buffer}, [foo_route])

    # Expect "bar" events in trials 0 and 3, before the wrt times.
    bar_reader = FakeNumericEventReader(script=[[[0.1, 1]], [[3.1, 0]]])
    bar_buffer = NumericEventBuffer()
    bar_route = ReaderRoute("events", "bar")
    bar_router = ReaderRouter(bar_reader, {"bar": bar_buffer}, [bar_route])

    extractor = TrialExtractor(
        wrt_buffer,
        wrt_value=42,
        named_buffers={
            "foo": foo_buffer,
            "bar": bar_buffer
        }
    )

    # Trial zero should cover whatever happened before the first "start" event.
    # This might be non-task rig setup data, or just garbage, or whatever.
    assert start_router.route_next() == True
    trial_zero = delimiter.next()
    assert len(trial_zero) == 1
    assert trial_zero[0] == Trial(0.0, 1.0)

    # Now that we know a trial end time, ask each reader to read until just past that time.
    assert wrt_router.route_until(1.0) == 1.5
    assert foo_router.route_until(1.0) == 1.3
    assert bar_router.route_until(1.0) == 3.1

    # Now that all the readers are caught up to the trial end time, extract the trial data.
    extractor.populate_trial(trial_zero[0])
    assert trial_zero[0] == Trial(
        start_time=0,
        end_time=1.0,
        wrt_time=0.0,
        numeric_events={
            "foo": NumericEventList(np.array([[0.2, 0]])),
            "bar": NumericEventList(np.array([[0.1, 1]]))
        }
    )

    # Trials 1 and 2 should be "normal" trials with task data.
    assert start_router.route_next() == True
    trial_one = delimiter.next()
    assert len(trial_one) == 1
    assert trial_one[0] == Trial(1.0, 2.0)

    # Bar reader has already read past trial 1, which is fine, this can be a safe no-op.
    assert wrt_router.route_until(2.0) == 2.6
    assert foo_router.route_until(2.0) == 2.3
    assert bar_router.route_until(2.0) == 3.1
    extractor.populate_trial(trial_one[0])
    assert trial_one[0] == Trial(
        start_time=1.0,
        end_time=2.0,
        wrt_time=1.5,
        numeric_events={
            "foo": NumericEventList(np.array([[1.2 - 1.5, 0], [1.3 - 1.5, 1]])),
            "bar": NumericEventList(np.empty([0, 2]))
        }
    )

    assert start_router.route_next() == True
    trial_two = delimiter.next()
    assert len(trial_two) == 1
    assert trial_two[0] == Trial(2.0, 3.0)

    # Bar reader has already read past trial 2, which is still fine, this can be a safe no-op.
    assert wrt_router.route_until(3.0) == 3.5
    assert foo_router.route_until(3.0) == 2.3
    assert bar_router.route_until(3.0) == 3.1
    extractor.populate_trial(trial_two[0])
    assert trial_two[0] == Trial(
        start_time=2.0,
        end_time=3.0,
        wrt_time=2.5,
        numeric_events={
            "foo": NumericEventList(np.array([[2.2 - 2.5, 0], [2.3 - 2.5, 1]])),
            "bar": NumericEventList(np.empty([0, 2]))
        }
    )

    # We should now run out of "start" events
    assert start_router.route_next() == False

    # Now we make the last trial with whatever's left on all the readers.
    trial_three = delimiter.last()
    assert trial_three == Trial(3.0, None)
    assert wrt_router.route_next() == False
    assert foo_router.route_next() == False
    assert bar_router.route_next() == False
    extractor.populate_trial(trial_three)
    assert trial_three == Trial(
        start_time=3.0,
        end_time=None,
        wrt_time=3.5,
        numeric_events={
            "foo": NumericEventList(np.empty([0, 2])),
            "bar": NumericEventList(np.array([[3.1 - 3.5, 0]]))
        }
    )


def test_populate_trials_from_shared_buffers():
    # Expect trials starting at times 0, 1, 2, and 3.
    # Mix in the wrt times half way through trials 1, 2, and 3.
    start_reader = FakeNumericEventReader(
        script=[
            [[1, 1010]],
            [[1.5, 42]],
            [[2, 1010]],
            [[2.5, 42], [2.6, 42]],
            [[3, 1010]],
            [[3.5, 42]]
        ]
    )
    start_buffer = NumericEventBuffer()
    start_route = ReaderRoute("events", "start")
    wrt_buffer = NumericEventBuffer()
    wrt_route = ReaderRoute("events", "wrt")
    start_router = ReaderRouter(start_reader, {"start": start_buffer, "wrt": wrt_buffer}, [start_route, wrt_route])

    delimiter = TrialDelimiter(start_buffer, 1010)

    # Expect "foo" events in trials 0, 1, and 2, before the wrt times.
    foo_reader = FakeNumericEventReader(script=[[[0.2, 0]], [[1.2, 0], [1.3, 1]], [[2.2, 0], [2.3, 1]]])
    foo_buffer = NumericEventBuffer()
    foo_route = ReaderRoute("events", "foo")
    foo_router = ReaderRouter(foo_reader, {"foo": foo_buffer}, [foo_route])

    # Expect "bar" events in trials 0 and 3, before the wrt times.
    bar_reader = FakeNumericEventReader(script=[[[0.1, 1]], [[3.1, 0]]])
    bar_buffer = NumericEventBuffer()
    bar_route = ReaderRoute("events", "bar")
    bar_router = ReaderRouter(bar_reader, {"bar": bar_buffer}, [bar_route])

    extractor = TrialExtractor(
        wrt_buffer,
        wrt_value=42,
        named_buffers={
            "foo": foo_buffer,
            "bar": bar_buffer
        }
    )

    # Trial zero should cover whatever happened before the first "start" event.
    # This might be non-task rig setup data, or just garbage, or whatever.
    assert start_router.route_next() == True
    trial_zero = delimiter.next()
    assert len(trial_zero) == 1
    assert trial_zero[0] == Trial(0.0, 1.0)

    # Now that we know a trial end time, ask each reader to read until just past that time.
    assert start_router.route_until(1.0) == 1.0
    assert foo_router.route_until(1.0) == 1.3
    assert bar_router.route_until(1.0) == 3.1

    # Now that all the readers are caught up to the trial end time, extract the trial data.
    extractor.populate_trial(trial_zero[0])
    assert trial_zero[0] == Trial(
        start_time=0,
        end_time=1.0,
        wrt_time=0.0,
        numeric_events={
            "foo": NumericEventList(np.array([[0.2, 0]])),
            "bar": NumericEventList(np.array([[0.1, 1]]))
        }
    )

    # Trials 1 and 2 should be "normal" trials with task data.
    assert start_router.route_next() == True
    assert start_router.route_next() == True
    trial_one = delimiter.next()
    assert len(trial_one) == 1
    assert trial_one[0] == Trial(1.0, 2.0)

    # Bar reader has already read past trial 1, which is fine, this can be a safe no-op.
    assert start_router.route_until(2.0) == 2.0
    assert foo_router.route_until(2.0) == 2.3
    assert bar_router.route_until(2.0) == 3.1
    extractor.populate_trial(trial_one[0])
    assert trial_one[0] == Trial(
        start_time=1.0,
        end_time=2.0,
        wrt_time=1.5,
        numeric_events={
            "foo": NumericEventList(np.array([[1.2 - 1.5, 0], [1.3 - 1.5, 1]])),
            "bar": NumericEventList(np.empty([0, 2]))
        }
    )

    assert start_router.route_next() == True
    assert start_router.route_next() == True
    trial_two = delimiter.next()
    assert len(trial_two) == 1
    assert trial_two[0] == Trial(2.0, 3.0)

    # Bar reader has already read past trial 2, which is still fine, this can be a safe no-op.
    assert start_router.route_until(3.0) == 3.0
    assert foo_router.route_until(3.0) == 2.3
    assert bar_router.route_until(3.0) == 3.1
    extractor.populate_trial(trial_two[0])
    assert trial_two[0] == Trial(
        start_time=2.0,
        end_time=3.0,
        wrt_time=2.5,
        numeric_events={
            "foo": NumericEventList(np.array([[2.2 - 2.5, 0], [2.3 - 2.5, 1]])),
            "bar": NumericEventList(np.empty([0, 2]))
        }
    )

    # We should eventually run out of "wrt" and "start" events
    assert start_router.route_next() == True
    assert start_router.route_next() == False

    # Now we make the last trial with whatever's left on all the readers.
    trial_three = delimiter.last()
    assert trial_three == Trial(3.0, None)
    assert start_router.route_next() == False
    assert foo_router.route_next() == False
    assert bar_router.route_next() == False
    extractor.populate_trial(trial_three)
    assert trial_three == Trial(
        start_time=3.0,
        end_time=None,
        wrt_time=3.5,
        numeric_events={
            "foo": NumericEventList(np.empty([0, 2])),
            "bar": NumericEventList(np.array([[3.1 - 3.5, 0]]))
        }
    )
