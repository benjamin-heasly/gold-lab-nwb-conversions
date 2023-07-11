from typing import Any

from pyramid.trials.trials import Trial, TrialEnhancer


class TrialDurationEnhancer(TrialEnhancer):
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
