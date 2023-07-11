from typing import Any

from pyramid.trials.trials import Trial, TrialEnhancer


class TrialDurationEnhancer(TrialEnhancer):
    def enhance(self, trial: Trial) -> dict[str, Any]:
        if trial.end_time is None:
            return {"duration": None}
        else:
            return {"duration": trial.end_time - trial.start_time}
