import numpy as np

from pyramid.model.events import NumericEventList
from pyramid.trials.trials import Trial, TrialEnhancer
from pyramid.trials.standard_enhancers import PairedCodesEnhancer


def test_paired_codes_enhancer():
    code_names = {
        "foo": 42,
        "bar": 43,
        "baz": 44,
        "quux": 45,
    }
    enhancer = PairedCodesEnhancer(
        buffer_name="propcodes",
        code_names=code_names,
        value_min=2000,
        value_offset=3000,
        value_max=4000,
        value_scale=0.25
    )

    paired_code_data = [
        [0.0, 42.0],    # code for property "foo"
        [1, 3000],      # value 0
        [2, 43],        # code for property "bar"
        [3, 3005],      # value 1.25
        [4, 13],        # irrelevant
        [5, 44],        # code for property "baz"
        [6, 10000],     # irrelevant
        [7, 3600],      # value 150
        [8, 44],        # code for property "baz" (again)
        [9, 13],        # irrelevant
        [10, 3604],     # value 151
        [11, 45],       # code for property "quux"
        [12, 14],       # irrelevant
        [13, 20002],    # irrelevant
        [14, 15],       # irrelevant
        [15, 16],       # irrelevant
        [16, 3101],      # value 25.25
    ]
    event_list = NumericEventList(event_data=np.array(paired_code_data))
    trial = Trial(
        start_time=0,
        end_time=20,
        wrt_time=0,
        numeric_events={
            "propcodes": event_list
        }
    )

    enhancements = enhancer.enhance(trial, 0, {}, {})
    expected_enhancements = {
        "foo": 0.0,
        "bar": 1.25,
        "baz": 151.0,
        "quux": 25.25,
    }
    assert enhancements == expected_enhancements
