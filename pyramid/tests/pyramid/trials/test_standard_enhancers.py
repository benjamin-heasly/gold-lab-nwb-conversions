from pathlib import Path
import numpy as np

from pyramid.model.events import NumericEventList
from pyramid.trials.trials import Trial
from pyramid.trials.standard_enhancers import PairedCodesEnhancer


def test_paired_codes_enhancer(tmp_path):
    # Write out a .csv file with rules in it.
    rules_csv = Path(tmp_path, "rules.csv")
    with open(rules_csv, 'w') as f:
        f.write('type,value,name,base,min,max,scale,comment\n')
        f.write('id,42,foo,3000,2000,4000,0.25,this is just a comment\n')
        f.write('id,43,bar,3000,2000,4000,0.25,this is just a comment\n')
        f.write('value,44,baz,3000,2000,4000,0.25,this is just a comment\n')
        f.write('value,45,quux,3000,2000,4000,0.025,this is just a comment\n')
        f.write('ignore,777,ignore_me,3000,2000,4000,0.25,this is just a comment\n')

    enhancer = PairedCodesEnhancer(
        buffer_name="propcodes",
        rules_csv=rules_csv
    )

    # The "id" and "value" types should be included.
    assert 42 in enhancer.rules.keys()
    assert 43 in enhancer.rules.keys()
    assert 44 in enhancer.rules.keys()
    assert 45 in enhancer.rules.keys()

    # Other types should ne ignored.
    assert 777 not in enhancer.rules.keys()

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
        [16, 3101],     # value 2.525 (quux has scale 10 time finer than the others)
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

    enhancer.enhance(trial, 0, {}, {})
    expected_enhancements = {
        "id": {
            "foo": 0.0,
            "bar": 1.25,
        },
        "value": {
            "baz": 151.0,
            "quux": 2.5250000000000004,
        }
    }
    assert trial.enhancements == expected_enhancements
