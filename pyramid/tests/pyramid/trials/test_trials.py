from typing import Any
import numpy as np

from pyramid.model.model import Buffer, BufferData
from pyramid.model.events import NumericEventList
from pyramid.model.signals import SignalChunk
from pyramid.neutral_zone.readers.readers import Reader, ReaderRoute, ReaderRouter
from pyramid.trials.trials import Trial, TrialDelimiter, TrialExtractor, TrialEnhancer
from pyramid.trials.standard_enhancers import TrialDurationEnhancer


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

    def get_initial(self) -> dict[str, BufferData]:
        return {
            "events": NumericEventList(np.empty([0, 2]))
        }


def router_for_reader_and_routes(reader: Reader, routes: list[ReaderRoute]):
    initial_results = reader.get_initial()
    named_buffers = {}
    for route in routes:
        if route.results_key in initial_results:
            named_buffers[route.buffer_name] = Buffer(initial_results[route.results_key].copy())
    return ReaderRouter(reader, routes, named_buffers)


def test_delimit_trials_from_pivate_buffer():
    start_reader = FakeNumericEventReader(script=[[[1, 1010]], [[2, 1010]], [[3, 1010]]])
    start_route = ReaderRoute("events", "start")
    start_router = router_for_reader_and_routes(start_reader, [start_route])

    # Log every other trial, just to get code coverage on the logging conditional!
    delimiter = TrialDelimiter(start_router.buffers["start"], 1010, trial_log_mod=2)

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
    start_route = ReaderRoute("events", "start")
    start_router = router_for_reader_and_routes(start_reader, [start_route])

    delimiter = TrialDelimiter(start_router.buffers["start"], 1010)

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
    start_route = ReaderRoute("events", "start")
    start_router = router_for_reader_and_routes(start_reader, [start_route])

    delimiter = TrialDelimiter(start_router.buffers["start"], 1010)

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
    start_route = ReaderRoute("events", "start")
    start_router = router_for_reader_and_routes(start_reader, [start_route])

    delimiter = TrialDelimiter(start_router.buffers["start"], 1010)

    # Expect wrt times half way through trials 1, 2, and 3.
    wrt_reader = FakeNumericEventReader(script=[[[1.5, 42]], [[2.5, 42], [2.6, 42]], [[3.5, 42]]])
    wrt_route = ReaderRoute("events", "wrt")
    wrt_router = router_for_reader_and_routes(wrt_reader, [wrt_route])

    # Expect "foo" events in trials 0, 1, and 2, before the wrt times.
    foo_reader = FakeNumericEventReader(script=[[[0.2, 0]], [[1.2, 0], [1.3, 1]], [[2.2, 0], [2.3, 1]]])
    foo_route = ReaderRoute("events", "foo")
    foo_router = router_for_reader_and_routes(foo_reader, [foo_route])

    # Expect "bar" events in trials 0 and 3, before the wrt times.
    bar_reader = FakeNumericEventReader(script=[[[0.1, 1]], [[3.1, 0]]])
    bar_route = ReaderRoute("events", "bar")
    bar_router = router_for_reader_and_routes(bar_reader, [bar_route])

    extractor = TrialExtractor(
        wrt_router.buffers["wrt"],
        wrt_value=42,
        named_buffers={
            "foo": foo_router.buffers["foo"],
            "bar": bar_router.buffers["bar"]
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
    extractor.populate_trial(trial_zero[0], delimiter.trial_count, {}, {})
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
    extractor.populate_trial(trial_one[0], delimiter.trial_count, {}, {})
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
    extractor.populate_trial(trial_two[0], delimiter.trial_count, {}, {})
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
    extractor.populate_trial(trial_three, delimiter.trial_count, {}, {})
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
    start_route = ReaderRoute("events", "start")
    wrt_route = ReaderRoute("events", "wrt")
    start_router = router_for_reader_and_routes(start_reader, [start_route, wrt_route])

    delimiter = TrialDelimiter(start_router.buffers["start"], 1010)

    # Expect "foo" events in trials 0, 1, and 2, before the wrt times.
    foo_reader = FakeNumericEventReader(script=[[[0.2, 0]], [[1.2, 0], [1.3, 1]], [[2.2, 0], [2.3, 1]]])
    foo_route = ReaderRoute("events", "foo")
    foo_router = router_for_reader_and_routes(foo_reader, [foo_route])

    # Expect "bar" events in trials 0 and 3, before the wrt times.
    bar_reader = FakeNumericEventReader(script=[[[0.1, 1]], [[3.1, 0]]])
    bar_route = ReaderRoute("events", "bar")
    bar_router = router_for_reader_and_routes(bar_reader, [bar_route])

    extractor = TrialExtractor(
        start_router.buffers["wrt"],
        wrt_value=42,
        named_buffers={
            "foo": foo_router.buffers["foo"],
            "bar": bar_router.buffers["bar"]
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
    extractor.populate_trial(trial_zero[0], delimiter.trial_count, {}, {})
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
    extractor.populate_trial(trial_one[0], delimiter.trial_count, {}, {})
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
    extractor.populate_trial(trial_two[0], delimiter.trial_count, {}, {})
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
    extractor.populate_trial(trial_three, delimiter.trial_count, {}, {})
    assert trial_three == Trial(
        start_time=3.0,
        end_time=None,
        wrt_time=3.5,
        numeric_events={
            "foo": NumericEventList(np.empty([0, 2])),
            "bar": NumericEventList(np.array([[3.1 - 3.5, 0]]))
        }
    )


class DurationPlusTrialCount(TrialEnhancer):
    """Nonsense calculation just to test enhancement ordering and passed-in data."""

    def enhance(
        self,
        trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> dict[str, Any]:
        duration = trial.enhancements["value"]["duration"]
        if duration is None:
            duration_plus_trial_count = None
        else:
            duration_plus_trial_count = duration + trial_count
        trial.add_enhancement("duration_plus_trial_count", duration_plus_trial_count, "value")


class BadEnhancer(TrialEnhancer):
    """Nonsense enhancer that always errors."""

    def enhance(
        self,
        trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        raise RuntimeError


def test_enhance_trials():
    # Expect trials with slightly increasing durations
    start_reader = FakeNumericEventReader(script=[[[1, 1010]], [[2.1, 1010]], [[3.3, 1010]]])
    start_route = ReaderRoute("events", "start")
    start_router = router_for_reader_and_routes(start_reader, [start_route])

    delimiter = TrialDelimiter(start_router.buffers["start"], 1010)

    # Expect wrt times half way through trials 1, 2, and 3.
    wrt_reader = FakeNumericEventReader(script=[[[1.5, 42]], [[2.5, 42], [2.6, 42]], [[3.5, 42]]])
    wrt_route = ReaderRoute("events", "wrt")
    wrt_router = router_for_reader_and_routes(wrt_reader, [wrt_route])

    # Enhance trials with a sequence of enhancers.
    # The middle one always errors -- which should not blow up the overall process.
    enhancers = [TrialDurationEnhancer(), BadEnhancer(), DurationPlusTrialCount()]

    extractor = TrialExtractor(
        wrt_router.buffers["wrt"],
        wrt_value=42,
        enhancers=enhancers
    )

    # Trial zero should cover whatever happened before the first "start" event.
    # This might be non-task rig setup data, or just garbage, or whatever.
    assert start_router.route_next() == True
    trial_zero = delimiter.next()
    assert len(trial_zero) == 1
    assert trial_zero[0] == Trial(0.0, 1.0)

    assert wrt_router.route_until(1.0) == 1.5
    extractor.populate_trial(trial_zero[0], delimiter.trial_count, {}, {})
    assert trial_zero[0] == Trial(
        start_time=0,
        end_time=1.0,
        wrt_time=0.0,
        enhancements={
            "value": {
                "duration": 1.0,
                "duration_plus_trial_count": 2.0
            }
        }
    )

    # Trials 1 and 2 should be "normal" trials with task data.
    assert start_router.route_next() == True
    trial_one = delimiter.next()
    assert len(trial_one) == 1
    assert trial_one[0] == Trial(1.0, 2.1)

    assert wrt_router.route_until(2.1) == 2.6
    extractor.populate_trial(trial_one[0], delimiter.trial_count, {}, {})
    assert trial_one[0] == Trial(
        start_time=1.0,
        end_time=2.1,
        wrt_time=1.5,
        enhancements={
            "value": {
                "duration": 1.1,
                "duration_plus_trial_count": 3.1
            }
        }
    )

    assert start_router.route_next() == True
    trial_two = delimiter.next()
    assert len(trial_two) == 1
    assert trial_two[0] == Trial(2.1, 3.3)

    assert wrt_router.route_until(3.3) == 3.5
    extractor.populate_trial(trial_two[0], delimiter.trial_count, {}, {})
    assert trial_two[0] == Trial(
        start_time=2.1,
        end_time=3.3,
        wrt_time=2.5,
        enhancements={
            "value": {
                "duration": 3.3 - 2.1,
                "duration_plus_trial_count": 3 + 3.3 - 2.1
            }
        }
    )

    # We should now run out of "start" events
    assert start_router.route_next() == False
    trial_three = delimiter.last()
    assert trial_three == Trial(3.3, None)
    assert wrt_router.route_next() == False
    extractor.populate_trial(trial_three, delimiter.trial_count, {}, {})
    assert trial_three == Trial(
        start_time=3.3,
        end_time=None,
        wrt_time=3.5,
        enhancements={
            "value": {
                "duration": None,
                "duration_plus_trial_count": None
            }
        }
    )


def test_add_buffer_data():
    event_list = NumericEventList(np.array([[0, 0]]))
    signal_chunk = SignalChunk(
        sample_data=NumericEventList(np.array([[0, 0], [1, 1]])),
        sample_frequency=1.0,
        first_sample_time=0.0,
        channel_ids=["a", "b"]
    )

    trial = Trial(start_time=0.0, end_time=1.0)

    # Buffer data should be added by name and type.
    assert trial.add_buffer_data("events", event_list)
    assert trial.add_buffer_data("signal", signal_chunk)

    # Buffer data must be a BufferData type.
    assert not trial.add_buffer_data("int", 42)
    assert not trial.add_buffer_data("string", "a string!")

    # Enhancements should be added by name in the default "other" category.
    assert trial.add_enhancement("int", 42)
    assert trial.add_enhancement("string", "a string!")

    # Enhancements should be added by name in a given category.
    assert trial.add_enhancement("int", 42, "my_category")
    assert trial.add_enhancement("string", "a string!", "my_category")

    # Enhancements that are a BufferData type should be added by name and type.
    assert trial.add_enhancement("events_2", event_list)
    assert trial.add_enhancement("signal_2", signal_chunk)

    expected_trial = Trial(
        start_time=0.0,
        end_time=1.0,
        numeric_events={
            "events": event_list,
            "events_2": event_list
        },
        signals={
            "signal": signal_chunk,
            "signal_2": signal_chunk
        },
        enhancements={
            "other": {
                "int": 42,
                "string": "a string!"
            },
            "my_category": {
                "int": 42,
                "string": "a string!"
            }
        }
    )
    assert trial == expected_trial
