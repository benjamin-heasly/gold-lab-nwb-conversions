import numpy as np

from pyramid.model import NumericEventList

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

    event_list.apply_offset_then_gain(offset=-500, gain = 2)
    assert np.array_equal(event_list.get_times(), np.array(range(40, 60)))
    print(event_list.get_values())
    assert np.array_equal(event_list.get_values(), 2*10*np.array(range(-10, 10)))

def test_numeric_event_list_interop():
    event_count = 100
    raw_data = [[t, 10*t] for t in range(event_count)]
    event_data = np.array(raw_data)
    event_list = NumericEventList(event_data)

    generic = event_list.to_generic()
    event_list_2 = NumericEventList.from_generic(generic)
    assert np.array_equal(event_list_2.event_data, event_list.event_data)

    generic_2 = event_list_2.to_generic()
    assert generic_2 == generic
