import time
from matplotlib.figure import Figure

from pyramid.plotters.plotters import Plotter


class BasicInfoPlotter(Plotter):

    def set_up(self, fig: Figure, experiment_info={}, subject_info={}) -> None:
        ax = fig.subplots()
        ax.axis("off")
        self.table = ax.table(
            cellText=[
                ["pyramid elapsed:", 0],
                ["trial count:", 0],
                ["last trial start:", 0],
                ["last trial wrt:", 0],
                ["last trial end:", 0],
            ],
            cellLoc="left",
            loc="center"
        )
        self.start_time = time.time()

    def update(self, fig, current_trial, trials_info, experiment_info={}, subject_info={}) -> None:
        elapsed = time.time() - self.start_time
        self.table.get_celld()[(0, 1)].get_text().set_text(elapsed)
        self.table.get_celld()[(1, 1)].get_text().set_text(trials_info["trial_count"])
        self.table.get_celld()[(2, 1)].get_text().set_text(current_trial.start_time)
        self.table.get_celld()[(3, 1)].get_text().set_text(current_trial.wrt_time)
        self.table.get_celld()[(4, 1)].get_text().set_text(current_trial.end_time)

    def clean_up(self, fig: Figure) -> None:
        pass
