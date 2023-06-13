import numpy as np

from pyramid.numeric_events import NumericEventList, NumericEventReader


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


class TrivialNumericEventReader(NumericEventReader):

    def __init__(self, schedule=list(range(10))) -> None:
        self.counter = -1
        self.schedule = schedule

    def read_next(self, timeout: float) -> NumericEventList:
        # Incrementing this counter is like consuming a system or library resource:
        # - advance a file cursor
        # - increment past a file data block
        # - poll a netowork connection
        self.counter += 1

        # Return dummy events on some schedule, allowing us to test retry logic.
        if timeout > 0 and self.counter in self.schedule:
            raw_data = [[self.counter, 10*self.counter]]
            return NumericEventList(np.array(raw_data))
        else:
            return None