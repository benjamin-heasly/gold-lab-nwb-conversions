from typing import Any

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
    ) -> dict[str, Any]:
        if trial.end_time is None:
            return {"duration": None}
        else:
            return {"duration": trial.end_time - trial.start_time}


class PairedCodesEnhancer(TrialEnhancer):
    """Look for pairs of numeric events that represent property-value pairs."""

    def __init__(
        self,
        buffer_name: str,
        code_names: dict[str, int],
        value_min: int = 0,
        value_offset: int = 0,
        value_max: int = 1000,
        value_scale: float = 1.0,
        value_index: int = 0
    ) -> None:
        self.buffer_name = buffer_name
        self.property_codes = code_names
        self.value_min = value_min
        self.value_offset = value_offset
        self.value_max = value_max
        self.value_scale = value_scale
        self.value_index = value_index

    def enhance(
        self,
        trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> dict[str, Any]:
        event_list = trial.numeric_events[self.buffer_name]
        value_list = event_list.copy_value_range(min=self.value_min, max=self.value_max, value_index=self.value_index)
        value_list.apply_offset_then_gain(-self.value_offset, self.value_scale)

        enhancements = {}
        for name, code in self.property_codes.items():
            property_times = event_list.get_times_of(code, self.value_index)
            for property_time in property_times:
                values = value_list.get_values(start_time=property_time, value_index=self.value_index)
                if values.size > 0:
                    enhancements[name] = values[0]

        return enhancements