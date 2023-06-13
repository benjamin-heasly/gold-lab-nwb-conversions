import numpy as np

from pyramid.numeric_events import NumericEventList
from pyramid.trials import Trial


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
