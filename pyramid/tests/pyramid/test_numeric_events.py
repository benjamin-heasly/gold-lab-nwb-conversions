import numpy as np

from pyramid.numeric_events import NumericEventList, NumericEventReader, NumericEventSource


def test_list_getters():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    assert event_list.event_count() == event_count
    assert event_list.values_per_event() == 1
    assert np.array_equal(event_list.get_times(), np.array(range(event_count)))
    assert np.array_equal(event_list.get_values(), 10*np.array(range(event_count)))

    assert np.array_equal(event_list.get_times_of(0.0), np.array([0.0]))
    assert np.array_equal(event_list.get_times_of(10.0), np.array([1.0]))
    assert np.array_equal(event_list.get_times_of(990.0), np.array([99.0]))
    assert event_list.get_times_of(-1.0).size == 0
    assert event_list.get_times_of(10.42).size == 0
    assert event_list.get_times_of(1000).size == 0

    assert np.array_equal(event_list.get_times_of(50.0, start_time=4.0), np.array([5.0]))
    assert np.array_equal(event_list.get_times_of(50.0, start_time=5.0), np.array([5.0]))
    assert event_list.get_times_of(50.0, start_time=6.0).size == 0
    assert event_list.get_times_of(50.0, end_time=4.0).size == 0
    assert event_list.get_times_of(50.0, end_time=5.0).size == 0
    assert np.array_equal(event_list.get_times_of(50.0, end_time=6.0), np.array([5.0]))
    assert np.array_equal(event_list.get_times_of(50.0, start_time=4.0, end_time=6.0), np.array([5.0]))


def test_list_append():
    event_count = 100
    half_count = int(event_count / 2)
    event_list_a = NumericEventList(np.array([[t, 10*t] for t in range(half_count)]))
    event_list_b = NumericEventList(np.array([[t, 10*t] for t in range(half_count, event_count)]))
    event_list_a.append(event_list_b)

    assert event_list_a.event_count() == event_count
    assert event_list_a.values_per_event() == 1
    assert np.array_equal(event_list_a.get_times(), np.array(range(event_count)))
    assert np.array_equal(event_list_a.get_values(), 10*np.array(range(event_count)))


def test_list_discard_before():
    event_count = 100
    half_count = int(event_count / 2)
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    event_list.discard_before(half_count)
    assert np.array_equal(event_list.get_times(), np.array(range(half_count, event_count)))
    assert np.array_equal(event_list.get_values(), 10*np.array(range(half_count, event_count)))


def test_list_shift_times():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    event_list.shift_times(5)
    assert np.array_equal(event_list.get_times(), 5 + np.array(range(100)))


def test_list_transform_values():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    event_list.apply_offset_then_gain(offset=-500, gain=2)
    assert np.array_equal(event_list.get_times(), np.array(range(100)))
    assert np.array_equal(event_list.get_values(), 2*10*np.array(range(-50, 50)))


def test_list_copy_value_range():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    range_event_list = event_list.copy_value_range(min=400, max=600)
    assert np.array_equal(range_event_list.get_times(), np.array(range(40, 60)))
    assert np.array_equal(range_event_list.get_values(), 10*np.array(range(40, 60)))

    # original list should be unchanged
    assert np.array_equal(event_list.get_times(), np.array(range(100)))
    assert np.array_equal(event_list.get_values(), 10*np.array(range(100)))


def test_list_copy_time_range():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    range_event_list = event_list.copy_time_range(40, 60)
    assert np.array_equal(range_event_list.get_times(), np.array(range(40, 60)))
    assert np.array_equal(range_event_list.get_values(), 10*np.array(range(40, 60)))

    tail_event_list = event_list.copy_time_range(start_time=40)
    assert np.array_equal(tail_event_list.get_times(), np.array(range(40, event_count)))
    assert np.array_equal(tail_event_list.get_values(), 10*np.array(range(40, event_count)))

    head_event_list = event_list.copy_time_range(end_time=60)
    assert np.array_equal(head_event_list.get_times(), np.array(range(0, 60)))
    assert np.array_equal(head_event_list.get_values(), 10*np.array(range(0, 60)))

    # original list should be unchanged
    assert np.array_equal(event_list.get_times(), np.array(range(100)))
    assert np.array_equal(event_list.get_values(), 10*np.array(range(100)))


def test_list_interop():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    interop = event_list.to_interop()
    event_list_2 = NumericEventList.from_interop(interop)
    assert event_list_2 == event_list

    interop_2 = event_list_2.to_interop()
    assert interop_2 == interop


def test_list_equality():
    foo_events = NumericEventList(np.array([[t, 10*t] for t in range(100)]))
    bar_events = NumericEventList(np.array([[t/10, 2*t] for t in range(1000)]))
    baz_events = NumericEventList(np.array([[t/10, 2*t] for t in range(1000)]))

    assert foo_events == foo_events
    assert bar_events == bar_events
    assert baz_events == baz_events
    assert bar_events == baz_events
    assert baz_events == bar_events

    assert foo_events != bar_events
    assert bar_events != foo_events
    assert foo_events != baz_events
    assert baz_events != foo_events

    assert foo_events != "wrong type"
    assert bar_events != "wrong type"
    assert baz_events != "wrong type"


class FakeNumericEventReader(NumericEventReader):

    def __init__(
        self,
        script=[[0, 0],
                [1, 10],
                [2, 20],
                [3, 30],
                [4, 40],
                [5, 50],
                [6, 60],
                [7, 70],
                [8, 80],
                [9, 90]]
    ) -> None:
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
            return NumericEventList(np.array([self.script[self.index]]))
        else:
            return None


def test_read_idempotent():
    reader = FakeNumericEventReader()
    source = NumericEventSource(reader)
    assert source.start_time() == 0.0
    assert source.end_time() == 0.0

    all_caught_up = source.read_until_time(5)
    assert all_caught_up
    assert source.start_time() == 0.0
    assert source.end_time() == 5.0
    assert source.event_list.event_count() == 6

    # read_until_time sould be idempotent
    previous_index = reader.index
    all_caught_up_2 = source.read_until_time(5)
    assert all_caught_up_2
    assert reader.index == previous_index
    assert source.start_time() == 0.0
    assert source.end_time() == 5.0
    assert source.event_list.event_count() == 6


def test_read_incrementally():
    reader = FakeNumericEventReader()
    source = NumericEventSource(reader)

    for until in [2, 4, 6, 8]:
        all_caught_up = source.read_until_time(until)
        assert all_caught_up
        assert source.start_time() == 0.0
        assert source.end_time() == until
        assert source.event_list.event_count() == until + 1

    all_caught_up = source.read_until_time(10)
    assert not all_caught_up
    assert source.start_time() == 0.0
    assert source.end_time() == 9.0
    assert source.event_list.event_count() == 10


def test_read_timeout():
    reader = FakeNumericEventReader()
    source = NumericEventSource(reader, reader_timeout=0.0)

    all_caught_up = source.read_until_time(5)
    assert not all_caught_up
    assert source.start_time() == 0.0
    assert source.end_time() == 0.0
    assert source.event_list.event_count() == 0


def test_read_retry_success():
    # Contrive a script of reader data with a hole in it, to force reader retries.
    script = [[0, 0],
            [1, 10],
            [2, 20],
            [3, 30],
            [4, 40],
            None,
            [5, 50]]
    reader = FakeNumericEventReader(script=script)

    # Source will retry empty reads twice, so the hole should be no problem.
    source = NumericEventSource(reader, max_empty_reads=2)

    all_caught_up = source.read_until_time(5)
    assert all_caught_up
    assert source.start_time() == 0.0
    assert source.end_time() == 5.0
    assert source.event_list.event_count() == 6


def test_read_retries_exhausted():
    # Contrive a script of reader data with a large hole in it, to force reader retries.
    script = [[0, 0],
            [1, 10],
            [2, 20],
            [3, 30],
            [4, 40],
            None,
            None,
            None,
            [5, 50]]
    reader = FakeNumericEventReader(script=script)

    # Source will retry empty reads twice, which is smaller than the hole size
    source = NumericEventSource(reader, max_empty_reads=2)

    all_caught_up = source.read_until_time(5)
    assert not all_caught_up
    assert source.start_time() == 0.0
    assert source.end_time() == 4.0
    assert source.event_list.event_count() == 5
