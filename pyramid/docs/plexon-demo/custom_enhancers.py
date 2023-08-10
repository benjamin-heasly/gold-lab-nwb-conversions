from typing import Any
from pyramid.trials.trials import Trial, TrialEnhancer


class CustomEnhancer(TrialEnhancer):

    def enhance(
        self,
        trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:

        # Use trial.get_enhancement() to get values already set by PairedCodesEnhancer and ecode-rules.csv.

        task_id = trial.get_enhancement("task_id")
        if task_id is None:
            return
        trial_id = trial.get_enhancement("trial_id") - 100 * task_id

        # Use trial.add_enhancement() to set new values from custom computations.

        # correct_target: 1 or 2
        if task_id == 1:
            correct_target = 1
        else:
            if trial_id < 9:
                correct_target = 1
            else:
                correct_target = 2
        trial.add_enhancement("correct_target", correct_target, "id")

        # neg are close to T1, pos are close to T2
        trial.add_enhancement("sample_id", 0, "id")

        trial.add_enhancement("t1_angle", 42, "id")
        trial.add_enhancement("t2_angle", 42, "id")
        trial.add_enhancement("sample_angle", 42, "value")

        # evidence for T1 (-) vs T2 (+)
        trial.add_enhancement("llr", 42, "value")

        trial.add_enhancement("target_r", 42, "value")
        trial.add_enhancement("sac_angle", 42, "value")

        # 1=correct, 0=error, -1=nc, -2=brfix,-3=sample
        trial.add_enhancement("score", 42, "id")

        # online score: 1=correct, 0=error, -1=nc, -2=brfix
        trial.add_enhancement("online_score", 42, "value")

        # 0=neither, 1=T1, 2=T2
        trial.add_enhancement("choice", 42, "id")

        trial.add_enhancement("score_match", 42, "value")

        trial.add_enhancement("RT", 42, "value")

        trial.add_enhancement("sac_endx", 42, "value")
        trial.add_enhancement("sac_endy", 42, "value")
        trial.add_enhancement("sac_dur", 42, "value")
        trial.add_enhancement("sac_vmax", 42, "value")
        trial.add_enhancement("sac_amp", 42, "value")

# ang_def
# ang_diff
# subject-specific conditional
# extract saccades
# choose a saccade to save
# a custom plot
# get multiple ecode scalars for list of names
