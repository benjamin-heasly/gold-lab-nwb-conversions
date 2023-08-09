from typing import Any
import csv

from pyramid.trials.trials import Trial, TrialEnhancer


class TrialDurationEnhancer(TrialEnhancer):
    """A simple enhancer that computes trial duration, for demo and testing."""

    def __eq__(self, other: object) -> bool:
        """Compare enhancers just by type, to support use of this class in tests."""
        return isinstance(other, self.__class__)

    def enhance(
        self,
        trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        if trial.end_time is None:
            duration = None
        else:
            duration = trial.end_time - trial.start_time
        trial.add_enhancement("duration", duration, "value")


class PairedCodesEnhancer(TrialEnhancer):
    """Look for pairs of numeric events that represent property-value pairs.

    buffer_name is the name of a buffer of NumericEventList.

    rules_csv is a .csv file where each row contains a rule for how to extract a property from the
    named buffer.  The .csv must have the following columns:

        - "type": Used to select relevant rows of the .csv, and also the trial enhancement category to
                  use for each property.  By defalt only types "id" and "value" will be used.
                  Pass in rule_types to change this default.
        - "value": a numeric value that represents a property, for example 1010
        - "name": the string name to use for the property, for example "fp_on"
        - "min": the smallest event value to consier when looking for the property's value events
        - "max": the largest event value to consier when looking for the property's value events
        - "base": the base value to subtract from the property's value events, for example 7000
        - "scale": how to scale each event value after subtracting its base, for example 0.1

    The .csv may contain additional columns, which will be ignored (eg a "comment" column).

    value_index is which event value to look for, in the NumericEventList
    (default is 0, the first value for each event).

    rule_types is a list of strings to match against the .csv "type" column.
    The default is ["id", "value"].

    dialect and any additional fmtparams are passed on to the .csv reader.
    """

    def __init__(
        self,
        buffer_name: str,
        rules_csv: str,
        value_index: int = 0,
        rule_types: list[str] = ["id", "value"],
        dialect: str = 'excel',
        **fmtparams
    ) -> None:
        self.buffer_name = buffer_name
        self.rules_csv = rules_csv
        self.value_index = value_index
        self.rule_types = rule_types
        self.dialect = dialect
        self.fmtparams = fmtparams

        rules = {}
        with open(self.rules_csv, mode='r', newline='') as f:
            csv_reader = csv.DictReader(f, dialect=self.dialect, **self.fmtparams)
            for row in csv_reader:
                if row['type'] in self.rule_types:
                    value = float(row['value'])
                    rules[value] = {
                        'type': row['type'],
                        'name': row['name'],
                        'base': float(row['base']),
                        'min': float(row['min']),
                        'max': float(row['max']),
                        'scale': float(row['scale']),
                    }
        self.rules = rules

    def enhance(
        self,
        trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        event_list = trial.numeric_events[self.buffer_name]
        for value, rule in self.rules.items():
            # Did / when did this trial contain events indicating this rule/property?
            property_times = event_list.get_times_of(value, self.value_index)
            if property_times is not None and property_times.size > 0:
                # Get potential events that hold values for the indicated rule/property.
                value_list = event_list.copy_value_range(min=rule['min'], max=rule['max'], value_index=self.value_index)
                value_list.apply_offset_then_gain(-rule['base'], rule['scale'])
                for property_time in property_times:
                    # For each property event, pick the soonest value event that follows.
                    values = value_list.get_values(start_time=property_time, value_index=self.value_index)
                    if values.size > 0:
                        trial.add_enhancement(rule['name'], values[0], rule['type'])


class EventTimesEnhancer(TrialEnhancer):
    """Look for times when named events occurred.

    buffer_name is the name of a buffer of NumericEventList.

    rules_csv is a .csv file where each row contains a rule for how to extract events from the
    named buffer.  The .csv must have the following columns:

        - "type": Used to select relevant rows of the .csv, and also the trial enhancement category to
                  use for each property.  By defalt only the type "time" will be used.
                  Pass in rule_types to change this default.
        - "value": a numeric value that represents a property, for example 1010
        - "name": the string name to use for the property, for example "fp_on"

    The .csv may contain additional columns, which will be ignored (eg a "comment" column).

    value_index is which event value to look for, in the NumericEventList
    (default is 0, the first value for each event).

    rule_types is a list of strings to match against the .csv "type" column.
    The default is ["time"].

    dialect and any additional fmtparams are passed on to the .csv reader.
    """

    def __init__(
        self,
        buffer_name: str,
        rules_csv: str,
        value_index: int = 0,
        rule_types: list[str] = ["time"],
        dialect: str = 'excel',
        **fmtparams
    ) -> None:
        self.buffer_name = buffer_name
        self.rules_csv = rules_csv
        self.value_index = value_index
        self.rule_types = rule_types
        self.dialect = dialect
        self.fmtparams = fmtparams

        rules = {}
        with open(self.rules_csv, mode='r', newline='') as f:
            csv_reader = csv.DictReader(f, dialect=self.dialect, **self.fmtparams)
            for row in csv_reader:
                if row['type'] in self.rule_types:
                    value = float(row['value'])
                    rules[value] = {
                        'type': row['type'],
                        'name': row['name'],
                    }
        self.rules = rules

    def enhance(
        self,
        trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        event_list = trial.numeric_events[self.buffer_name]
        for value, rule in self.rules.items():
            # Did / when did this trial contain events of interest with the requested value?
            event_times = event_list.get_times_of(value, self.value_index)
            trial.add_enhancement(rule['name'], event_times.tolist(), rule['type'])
