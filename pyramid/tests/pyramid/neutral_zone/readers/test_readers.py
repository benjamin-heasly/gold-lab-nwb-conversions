import numpy as np

from pyramid.model.events import NumericEventList, NumericEventBuffer
from pyramid.neutral_zone.readers.readers import Reader, ReaderRoute, ReaderRouter
from pyramid.neutral_zone.transformers.standard_transformers import FilterRange, OffsetThenGain


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
            next = self.script[self.index]
            if not isinstance(next, list):
                raise ValueError("Numeric Event Reader needs a list of numbers!")

            return {
                "events": NumericEventList(np.array(next))
            }
        else:
            return None


def test_router_copy_events_to_buffers():
    reader = FakeNumericEventReader([[[0, 0]], [[1, 10]], [[2, 20]]])
    buffer_one = NumericEventBuffer()
    route_one = ReaderRoute("events", "one")
    buffer_two = NumericEventBuffer()
    route_two = ReaderRoute("events", "two")
    router = ReaderRouter(
        reader=reader,
        buffers={
            "one": buffer_one,
            "two": buffer_two
        },
        routes=[route_one, route_two]
    )

    assert router.max_buffer_time == 0

    # Copy events into both buffers, as they are read in.
    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 1
    assert buffer_two.event_list.event_count() == 1
    assert router.max_buffer_time == 0

    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 2
    assert buffer_two.event_list.event_count() == 2
    assert router.max_buffer_time == 1

    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 3
    assert buffer_two.event_list.event_count() == 3
    assert router.max_buffer_time == 2

    # OK to try routing new events when there are none left.
    assert router.route_next() == False
    assert buffer_one.event_list.event_count() == 3
    assert buffer_two.event_list.event_count() == 3
    assert router.max_buffer_time == 2

    # Confirm expected data in the buffers.
    assert buffer_one.event_list == NumericEventList(np.array([[0, 0], [1, 10], [2, 20]]))
    assert buffer_two.event_list == NumericEventList(np.array([[0, 0], [1, 10], [2, 20]]))

    # Confirm buffers contain independent copies of the data
    buffer_one.event_list.apply_offset_then_gain(offset=10, gain=2)
    assert buffer_one.event_list == NumericEventList(np.array([[0, 20], [1, 40], [2, 60]]))
    assert buffer_two.event_list == NumericEventList(np.array([[0, 0], [1, 10], [2, 20]]))


def test_router_tolerates_missing_results_or_buffers():
    reader = FakeNumericEventReader([[[0, 0]], [[1, 10]], [[2, 20]]])
    buffer_one = NumericEventBuffer()

    # Route one should work as expected, sending events into buffer one.
    route_one = ReaderRoute("events", "one")

    # Route two should do nothing, since there is no buffer two.
    route_two = ReaderRoute("events", "two")

    # Route three should do nothing, since there are no "missing" events.
    route_three = ReaderRoute("missing", "one")
    router = ReaderRouter(
        reader=reader,
        buffers={
            "one": buffer_one
        },
        routes=[route_one, route_two, route_three]
    )

    assert router.route_next() == True
    assert router.route_next() == True
    assert router.route_next() == True
    assert buffer_one.event_list == NumericEventList(np.array([[0, 0], [1, 10], [2, 20]]))


def test_router_circuit_breaker_for_reader_errors():
    reader = FakeNumericEventReader([[[0, 0]], [[1, 10]], "error!", [[2, 20]]])
    buffer_one = NumericEventBuffer()
    route_one = ReaderRoute("events", "one")
    router = ReaderRouter(
        reader=reader,
        buffers={
            "one": buffer_one,
        },
        routes=[route_one]
    )

    # First two reads should route data as normal.
    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 1
    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 2

    # Then the reader encounters an exception!
    # The router should circuit-break going forward, to prevent cascading errors.
    assert router.route_next() == False
    assert router.reader_exception is not None
    assert buffer_one.event_list.event_count() == 2
    assert router.route_next() == False
    assert buffer_one.event_list.event_count() == 2
    assert router.route_next() == False
    assert buffer_one.event_list.event_count() == 2


def test_router_skip_buffer_append_errors():
    reader = FakeNumericEventReader([[[0, 0]], [[1, 10]], [[2, 20, 200, 2000]], [[3, 30]]])
    buffer_one = NumericEventBuffer()
    route_one = ReaderRoute("events", "one")
    router = ReaderRouter(
        reader=reader,
        buffers={
            "one": buffer_one,
        },
        routes=[route_one]
    )

    # First two reads should route data as normal.
    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 1
    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 2

    # Third read has data of the wrong size, which will fail to append to the buffer.
    # The router should skip this and move on to prevent cascading errors.
    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 2

    # Fourth read should find well-formed data, again.
    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 3

    # Check all the well-formed data landed in the buffer.
    assert buffer_one.event_list == NumericEventList(np.array([[0, 0], [1, 10], [3, 30]]))


def test_router_routes_until_target_time():
    reader = FakeNumericEventReader([[[0, 0]], [[1, 10]], [[2, 20]], [[3, 30]]])
    buffer_one = NumericEventBuffer()
    route_one = ReaderRoute("events", "one")
    router = ReaderRouter(
        reader=reader,
        buffers={
            "one": buffer_one,
        },
        routes=[route_one]
    )

    # Router should read until an event arrives past the target time.
    # But not keep reading indefinitely after that.
    assert router.route_until(1.5) == 2

    # Once at the target time, router should not read any more.
    assert router.route_until(1.5) == 2
    assert router.route_until(1.5) == 2

    # Check expected events buffered up to and just past the target time.
    # But not way past the target time.
    assert buffer_one.event_list == NumericEventList(np.array([[0, 0], [1, 10], [2, 20]]))

    reader = FakeNumericEventReader([[[0, 0]], [[1, 10]], [[2, 20]], [[3, 30]]])
    buffer_one = NumericEventBuffer()
    route_one = ReaderRoute("events", "one")
    router = ReaderRouter(
        reader=reader,
        buffers={
            "one": buffer_one,
        },
        routes=[route_one]
    )

    # Router should read until an event arrives past the target time.
    # But not keep reading indefinitely after that.
    assert router.route_until(1.5) == 2

    # Once at the target time, router should not read any more.
    assert router.route_until(1.5) == 2
    assert router.route_until(1.5) == 2

    # Check expected events buffered up to and just past the target time.
    # But not way past the target time.
    assert buffer_one.event_list == NumericEventList(np.array([[0, 0], [1, 10], [2, 20]]))


def test_router_routes_until_target_time_with_retries():
    # The reader will have some gaps in the data that require retries to get passed.
    reader = FakeNumericEventReader([None, [[0, 0]], None, None, [[1, 10]], None, [[2, 20]], [[3, 30]]])
    buffer_one = NumericEventBuffer()
    route_one = ReaderRoute("events", "one")
    router = ReaderRouter(
        reader=reader,
        buffers={
            "one": buffer_one,
        },
        routes=[route_one],
        empty_reads_allowed=2
    )

    # As long as the data gaps are smaller than the router's empty_read_allowed limit,
    # The results should be the same as test_router_routes_until_target_time, above.

    # Router should read until an event arrives past the target time.
    # But not keep reading indefinitely after that.
    assert router.route_until(1.5) == 2

    # Once at the target time, router should not read any more.
    assert router.route_until(1.5) == 2
    assert router.route_until(1.5) == 2

    # Check expected events buffered up to and just past the target time.
    # But not way past the target time.
    assert buffer_one.event_list == NumericEventList(np.array([[0, 0], [1, 10], [2, 20]]))


def test_route_transforms_data():
    reader = FakeNumericEventReader([[[0, 0]], [[1, 10]], [[2, 20]]])
    buffer_one = NumericEventBuffer()
    route_one = ReaderRoute("events", "one")

    buffer_two = NumericEventBuffer()
    filter_range = FilterRange(min=10, max=20)
    offset_then_gain = OffsetThenGain(offset=42, gain=-1)
    route_two = ReaderRoute("events", "two", [filter_range, offset_then_gain])
    router = ReaderRouter(
        reader=reader,
        buffers={
            "one": buffer_one,
            "two": buffer_two
        },
        routes=[route_one, route_two]
    )

    # Copy events into both buffers.
    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 1
    assert buffer_two.event_list.event_count() == 0

    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 2
    assert buffer_two.event_list.event_count() == 1

    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 3
    assert buffer_two.event_list.event_count() == 1

    assert router.route_next() == False

    # Buffer one should get the original data.
    assert buffer_one.event_list == NumericEventList(np.array([[0, 0], [1, 10], [2, 20]]))

    # Buffer two should get transformed data.
    assert buffer_two.event_list == NumericEventList(np.array([[1, -52]]))


def test_router_skip_transformer_errors():
    reader = FakeNumericEventReader([[[0, 0]], [[1, 10]], [[2, 20]]])
    buffer_one = NumericEventBuffer()
    route_one = ReaderRoute("events", "one")

    buffer_two = NumericEventBuffer()
    filter_range = FilterRange(min="error!")
    route_two = ReaderRoute("events", "two", [filter_range])
    router = ReaderRouter(
        reader=reader,
        buffers={
            "one": buffer_one,
            "two": buffer_two
        },
        routes=[route_one, route_two]
    )

    # Copy events into both buffers.
    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 1
    assert buffer_two.event_list.event_count() == 0

    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 2
    assert buffer_two.event_list.event_count() == 0

    assert router.route_next() == True
    assert buffer_one.event_list.event_count() == 3
    assert buffer_two.event_list.event_count() == 0

    assert router.route_next() == False

    # Buffer one should get all the data.
    assert buffer_one.event_list == NumericEventList(np.array([[0, 0], [1, 10], [2, 20]]))

    # Buffer two should have had errors that didn't affect buffer one.
    assert buffer_two.event_list.event_count() == 0
