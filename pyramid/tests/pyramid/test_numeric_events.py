import numpy as np

from pyramid.numeric_events import NumericEventList


def test_counts():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    assert event_list.event_count() == event_count
    assert event_list.values_per_event() == 1
    assert np.array_equal(event_list.get_times(), np.array(range(event_count)))
    assert np.array_equal(event_list.get_values(), 10*np.array(range(event_count)))


def test_append():
    event_count = 100
    half_count = int(event_count / 2)
    event_list_a = NumericEventList(np.array([[t, 10*t] for t in range(half_count)]))
    event_list_b = NumericEventList(np.array([[t, 10*t] for t in range(half_count, event_count)]))
    event_list_a.append_events(event_list_b)

    assert event_list_a.event_count() == event_count
    assert event_list_a.values_per_event() == 1
    assert np.array_equal(event_list_a.get_times(), np.array(range(event_count)))
    assert np.array_equal(event_list_a.get_values(), 10*np.array(range(event_count)))


def test_shift_times():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    event_list.shift_times(5)
    assert np.array_equal(event_list.get_times(), 5 + np.array(range(100)))


def test_filter_times():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    event_list.filter_times(40, 60)
    assert np.array_equal(event_list.get_times(), np.array(range(40, 60)))
    assert np.array_equal(event_list.get_values(), 10*np.array(range(40, 60)))


def test_filter_values():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    event_list.filter_min_and_max(min=400, max=600)
    assert np.array_equal(event_list.get_times(), np.array(range(40, 60)))
    assert np.array_equal(event_list.get_values(), 10*np.array(range(40, 60)))


def test_transform_values():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    event_list.apply_offset_then_gain(offset=-500, gain=2)
    assert np.array_equal(event_list.get_times(), np.array(range(100)))
    assert np.array_equal(event_list.get_values(), 2*10*np.array(range(-50, 50)))


def test_interop():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    interop = event_list.to_interop()
    event_list_2 = NumericEventList.from_interop(interop)
    assert event_list_2 == event_list

    interop_2 = event_list_2.to_interop()
    assert interop_2 == interop


def test_equality():
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
