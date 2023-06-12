import numpy as np

from pyramid.model import NumericEventList, Trial


def test_numeric_event_list():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    assert event_list.event_count() == event_count
    assert event_list.values_per_event() == 1
    assert np.array_equal(event_list.get_times(), np.array(range(event_count)))
    assert np.array_equal(event_list.get_values(), 10*np.array(range(event_count)))

    event_list.filter_min_and_max(min=400, max=599)
    assert np.array_equal(event_list.get_times(), np.array(range(40, 60)))
    assert np.array_equal(event_list.get_values(), 10*np.array(range(40, 60)))

    event_list.apply_offset_then_gain(offset=-500, gain=2)
    assert np.array_equal(event_list.get_times(), np.array(range(40, 60)))
    print(event_list.get_values())
    assert np.array_equal(event_list.get_values(), 2*10*np.array(range(-10, 10)))


def test_numeric_event_list_interop():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    interop = event_list.to_interop()
    event_list_2 = NumericEventList.from_interop(interop)
    assert event_list_2 == event_list

    interop_2 = event_list_2.to_interop()
    assert interop_2 == interop


def test_trial_interop():
    start_time = 0
    end_time = 100
    wrt_time = 50
    trial = Trial(start_time, end_time, wrt_time)

    foo_events = NumericEventList(np.array([[t, 10*t] for t in range(100)]))
    trial.add_numeric_events("foo", foo_events)

    bar_events = NumericEventList(np.array([[t/10, 2*t] for t in range(1000)]))
    trial.add_numeric_events("bar", bar_events)

    interop = trial.to_interop()
    print(interop)
    trial_2 = Trial.from_interop(interop)
    assert trial_2 == trial

    interop_2 = trial_2.to_interop()
    assert interop_2 == interop
