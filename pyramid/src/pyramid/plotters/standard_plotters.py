import time
from binascii import crc32
from matplotlib.figure import Figure
from matplotlib.pyplot import get_cmap

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

    def __init__(self, history_size: int = 10, xmin: float = -2.0, xmax:float = 2.0) -> None:
        self.history_size = history_size
        self.history = []

        self.xmin = xmin
        self.xmax = xmax

    def set_up(self, fig: Figure, experiment_info={}, subject_info={}) -> None:
        self.ax = fig.subplots()
        self.ax.grid(which="major", axis="x")

    def update(self, fig, current_trial: Trial, trials_info, experiment_info={}, subject_info={}) -> None:
        self.ax.clear()

        # Show old events grayed-out.
        for old_events in self.history:
            for name, data in old_events.items():
                self.ax.scatter(data.get_times(), data.get_values(), color=name_to_color(name, 0.25))

        # Update finite, rolling history.
        new_events = current_trial.numeric_events
        self.history.append(new_events)
        self.history = self.history[-self.history_size:]

        # Show new events on top in full color.
        for name, data in new_events.items():
            self.ax.scatter(data.get_times(), data.get_values(), color=name_to_color(name), label=name)

        self.ax.set_xlim(xmin=self.xmin, xmax=self.xmax)
        self.ax.legend()

    def clean_up(self, fig: Figure) -> None:
        pass


class SignalChunksPlotter(Plotter):

    def __init__(self, history_size: int = 10, xmin: float = -2.0, xmax:float = 2.0, channel_ids: list[str|int] = None) -> None:
        self.history_size = history_size
        self.history = []

        self.xmin = xmin
        self.xmax = xmax
        self.channel_ids = channel_ids

    def set_up(self, fig: Figure, experiment_info={}, subject_info={}) -> None:
        self.ax = fig.subplots()
        self.ax.grid(which="major", axis="x")

    def update(self, fig, current_trial: Trial, trials_info, experiment_info={}, subject_info={}) -> None:
        self.ax.clear()

        # Show old events grayed-out.
        for old_chunks in self.history:
            for name, data in old_chunks.items():
                if self.channel_ids:
                    ids = self.channel_ids
                else:
                    ids = data.channel_ids
                for channel_id in ids:
                    full_name = f"{name} {channel_id}"
                    self.ax.plot(data.get_times(), data.get_channel_values(channel_id), color=name_to_color(full_name, 0.25))

        # Update finite, rolling history.
        new_signals = current_trial.signals
        self.history.append(new_signals)
        self.history = self.history[-self.history_size:]

        # Show new events on top in full color.
        for name, data in new_signals.items():
            if self.channel_ids:
                ids = self.channel_ids
            else:
                ids = data.channel_ids
            for channel_id in ids:
                full_name = f"{name} {channel_id}"
                self.ax.plot(data.get_times(), data.get_channel_values(channel_id), color=name_to_color(full_name), label=full_name)

        self.ax.set_xlim(xmin=self.xmin, xmax=self.xmax)
        self.ax.legend()

    def clean_up(self, fig: Figure) -> None:
        pass
