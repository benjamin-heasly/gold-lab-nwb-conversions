import time
from binascii import crc32
from matplotlib.figure import Figure
from matplotlib.cm import get_cmap

from pyramid.trials.trials import Trial
from pyramid.plotters.plotters import Plotter

color_map = get_cmap('Set1', 16)
def name_to_color(name: str, alpha: float = 1.0) -> str:
    hash = crc32(name.encode("utf-8"))
    index = hash % 16
    return color_map(index, alpha=alpha)


def format_number(number):
    if number is None:
        return ""
    else:
        return '{:.3f} sec'.format(number)

class BasicInfoPlotter(Plotter):

    def set_up(self, fig: Figure, experiment_info={}, subject_info={}) -> None:
        axes = fig.subplots(2,1)
        axes[0].axis("off")
        axes[1].axis("off")

        static_info = []
        if experiment_info:
            static_info += [[name, value] for name, value in experiment_info.items()]

        if subject_info:
            static_info += [[name, value] for name, value in subject_info.items()]
        
        if static_info:
            self.static_table = axes[0].table(
                cellText=static_info,
                cellLoc="left",
                loc="center"
            )

        self.trials_table = axes[1].table(
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

    def update(self, fig, current_trial: Trial, trials_info, experiment_info={}, subject_info={}) -> None:
        elapsed = time.time() - self.start_time
        self.trials_table.get_celld()[(0, 1)].get_text().set_text(format_number(elapsed))
        self.trials_table.get_celld()[(1, 1)].get_text().set_text(trials_info["trial_count"])
        self.trials_table.get_celld()[(2, 1)].get_text().set_text(format_number(current_trial.start_time))
        self.trials_table.get_celld()[(3, 1)].get_text().set_text(format_number(current_trial.wrt_time))
        self.trials_table.get_celld()[(4, 1)].get_text().set_text(format_number(current_trial.end_time))

    def clean_up(self, fig: Figure) -> None:
        pass



class NumericEventsPlotter(Plotter):

    def __init__(self, history_size: int = 10) -> None:
        self.history_size = history_size
        self.history = []

    def set_up(self, fig: Figure, experiment_info={}, subject_info={}) -> None:
        self.ax = fig.subplots()
        self.ax.grid(which="major", axis="x")

    def update(self, fig, current_trial: Trial, trials_info, experiment_info={}, subject_info={}) -> None:
        self.ax.clear()

        # Show old events grayed-out.
        for old_events in self.history:
            for name, data in old_events.items():
                self.ax.scatter(data.get_times(), data.get_values(), c=name_to_color(name, 0.5))

        # Update finite, rolling history.
        new_events = current_trial.numeric_events
        self.history.append(new_events)
        self.history = self.history[-self.history_size:]

        # Show new events on top in full color.
        for name, data in new_events.items():
            self.ax.scatter(data.get_times(), data.get_values(), c=name_to_color(name), label=name)

        self.ax.relim()
        self.ax.legend()

    def clean_up(self, fig: Figure) -> None:
        pass
