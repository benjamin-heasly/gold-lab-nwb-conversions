from typing import Any
import time
import re
from binascii import crc32

import numpy as np
from matplotlib.figure import Figure
from matplotlib.pyplot import get_cmap

from pyramid.trials.trials import Trial
from pyramid.plotters.plotters import Plotter


color_count = 14
color_map = get_cmap('brg', color_count)
def name_to_color(name: str, alpha: float = 1.0) -> str:
    hash = crc32(name.encode("utf-8"))
    index = hash % color_count
    return color_map(index, alpha=alpha)


def format_number(number):
    if number is None:
        return ""
    else:
        return '{:.3f} sec'.format(number)


class BasicInfoPlotter(Plotter):

    def set_up(
        self,
        fig: Figure,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        axes = fig.subplots(2,1)
        axes[0].set_title(f"Pyramid!")
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

    def update(
        self,
        fig: Figure,
        current_trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        elapsed = time.time() - self.start_time
        self.trials_table.get_celld()[(0, 1)].get_text().set_text(format_number(elapsed))
        self.trials_table.get_celld()[(1, 1)].get_text().set_text(trial_count)
        self.trials_table.get_celld()[(2, 1)].get_text().set_text(format_number(current_trial.start_time))
        self.trials_table.get_celld()[(3, 1)].get_text().set_text(format_number(current_trial.wrt_time))
        self.trials_table.get_celld()[(4, 1)].get_text().set_text(format_number(current_trial.end_time))

    def clean_up(self, fig: Figure) -> None:
        pass


class NumericEventsPlotter(Plotter):

    def __init__(
        self,
        history_size: int = 10,
        xmin: float = -2.0,
        xmax:float = 2.0,
        match_pattern: str = None,
        ylabel:str = None,
        value_index: int = 0,
        marker: str = "o"
    ) -> None:
        self.history_size = history_size
        self.history = []

        self.xmin = xmin
        self.xmax = xmax
        self.match_pattern = match_pattern
        self.ylabel = ylabel
        self.value_index = value_index
        self.marker = marker

    def set_up(
        self,
        fig: Figure,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        self.ax = fig.subplots()
        self.ax.set_axisbelow(True)

    def update(
        self,
        fig: Figure,
        current_trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        self.ax.clear()
        self.ax.grid(which="major", axis="both")
        self.ax.set_xlabel("trial time (s)")
        self.ax.set_ylabel(self.ylabel)

        if self.match_pattern:
            self.ax.set_title(f"Numeric Events: {self.match_pattern}")
        else:
            self.ax.set_title("Numeric Events")

        # Show old events faded out.
        for old in self.history:
            for name, data in old.items():
                self.ax.scatter(
                    data.get_times(),
                    data.get_values(value_index=self.value_index),
                    color=name_to_color(name, 0.125),
                    marker=self.marker
                )

        # Update finite, rolling history.
        new = {
            name: event_list
            for name, event_list in current_trial.numeric_events.items()
            if self.match_pattern is None or re.fullmatch(self.match_pattern, name) and event_list.event_count() > 0
        }
        self.history.append(new)
        self.history = self.history[-self.history_size:]

        # Show new events on top in full color.
        for name, data in new.items():
            self.ax.scatter(
                data.get_times(),
                data.get_values(value_index=self.value_index),
                color=name_to_color(name, 0.5),
                marker=self.marker,
                label=name
            )

        self.ax.set_xlim(xmin=self.xmin, xmax=self.xmax)
        self.ax.legend()

    def clean_up(self, fig: Figure) -> None:
        self.history = []


class SignalChunksPlotter(Plotter):

    def __init__(
        self,
        history_size: int = 10,
        xmin: float = -2.0,
        xmax:float = 2.0,
        channel_ids: list[str|int] = None,
        ylabel:str = None
        ) -> None:
        self.history_size = history_size
        self.history = []

        self.xmin = xmin
        self.xmax = xmax
        self.channel_ids = channel_ids
        self.ylabel = ylabel

    def set_up(
        self,
        fig: Figure,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        self.ax = fig.subplots()
        self.ax.set_axisbelow(True)

    def update(
        self,
        fig: Figure,
        current_trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        self.ax.clear()
        self.ax.grid(which="major", axis="both")
        self.ax.set_xlabel("trial time (s)")
        self.ax.set_ylabel(self.ylabel)

        if self.channel_ids:
            self.ax.set_title(f"Signals: {self.channel_ids}")
        else:
            self.ax.set_title("Signals")

        # Show old events faded out.
        for old_chunks in self.history:
            for name, data in old_chunks.items():
                if self.channel_ids:
                    ids = [channel_id for channel_id in self.channel_ids if channel_id in data.channel_ids]
                else:
                    ids = data.channel_ids
                for channel_id in ids:
                    full_name = f"{name} {channel_id}"
                    self.ax.plot(data.get_times(), data.get_channel_values(channel_id), color=name_to_color(full_name, 0.25))

        # Update finite, rolling history.
        new = current_trial.signals
        self.history.append(new)
        self.history = self.history[-self.history_size:]

        # Show new events on top in full color.
        for name, data in new.items():
            if self.channel_ids:
                ids = [channel_id for channel_id in self.channel_ids if channel_id in data.channel_ids]
            else:
                ids = data.channel_ids
            for channel_id in ids:
                full_name = f"{name} {channel_id}"
                self.ax.plot(data.get_times(), data.get_channel_values(channel_id), color=name_to_color(full_name), label=full_name)

        self.ax.set_xlim(xmin=self.xmin, xmax=self.xmax)
        self.ax.legend()

    def clean_up(self, fig: Figure) -> None:
        self.history = []


class EnhancementTimesPlotter(Plotter):

    def __init__(
        self,
        history_size: int = 10,
        xmin: float = -2.0,
        xmax:float = 2.0,
        enhancement_categories: list[str] = ["time"],
        match_pattern: str = None
    ) -> None:
        self.history_size = history_size
        self.history = []

        self.xmin = xmin
        self.xmax = xmax
        self.enhancement_categories = enhancement_categories
        self.match_pattern = match_pattern

    def set_up(
        self,
        fig: Figure,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        self.ax = fig.subplots()
        self.ax.set_axisbelow(True)
        self.all_names = []

    def update(
        self,
        fig: Figure,
        current_trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        self.ax.clear()
        self.ax.grid(which="major", axis="both")
        self.ax.set_xlabel("trial time (s)")

        if self.match_pattern:
            self.ax.set_title(f"Enhancement Times: {self.enhancement_categories} {self.match_pattern}")
        else:
            self.ax.set_title(f"Enhancement Times: {self.enhancement_categories}")

        # Show old events faded out.
        for old in self.history:
            for name, times in old.items():
                row = self.all_names.index(name)
                self.ax.scatter(times, row * np.ones([1, len(times)]), color=name_to_color(name, 0.25))

        # Update finite, rolling history.
        enhancement_names = []
        for category in self.enhancement_categories:
            enhancement_names += current_trial.enhancement_categories.get(category, [])

        new = {}
        for name in enhancement_names:
            if self.match_pattern is None or re.fullmatch(self.match_pattern, name):
                new[name] = current_trial.get_enhancement(name, [])
                if name not in self.all_names:
                    self.all_names.append(name)
        self.history.append(new)
        self.history = self.history[-self.history_size:]

        # Show new events on top in full color.
        for name, times in new.items():
            row = self.all_names.index(name)
            self.ax.scatter(times, row * np.ones([1, len(times)]), color=name_to_color(name), label=name)

        self.ax.set_yticks(range(len(self.all_names)), self.all_names)
        self.ax.set_xlim(xmin=self.xmin, xmax=self.xmax)

    def clean_up(self, fig: Figure) -> None:
        self.history = []

class EnhancementXYPlotter(Plotter):

    def __init__(
        self,
        xy_pairs: dict[str, str] = {},
        history_size: int = 10,
        xmin: float = -2.0,
        xmax:float = 2.0,
        ymin: float = -2.0,
        ymax:float = 2.0
    ) -> None:
        self.xy_pairs = xy_pairs

        self.history_size = history_size
        self.history = []

        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax

    def set_up(
        self,
        fig: Figure,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        self.ax = fig.subplots()
        self.ax.set_axisbelow(True)

    def update(
        self,
        fig: Figure,
        current_trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        self.ax.clear()
        self.ax.grid(which="major", axis="both")
        self.ax.set_title(f"XY Value Pairs")
        self.ax.set_xlabel("x")
        self.ax.set_ylabel("y")

        # Show old events faded out.
        for old in self.history:
            for name, point in old.items():
                self.ax.scatter(point[0], point[1], color=name_to_color(name, 0.25))

        new = {}
        for x_name, y_name in self.xy_pairs.items():
            x_value = current_trial.get_enhancement(x_name)
            y_value = current_trial.get_enhancement(y_name)
            if x_value is not None and y_value is not None:
                new[x_name] = (x_value, y_value)
        self.history.append(new)
        self.history = self.history[-self.history_size:]

        # Show new events on top in full color.
        for name, point in new.items():
            self.ax.scatter(point[0], point[1], color=name_to_color(name), label=name)

        self.ax.set_xlim(xmin=self.xmin, xmax=self.xmax)
        self.ax.set_ylim(ymin=self.ymin, ymax=self.ymax)
        self.ax.legend()

    def clean_up(self, fig: Figure) -> None:
        self.history = []

# TODO: "id" enhancements
# TODO: non-xy "value" enhancements
# TODO: saccades
# TODO: include in cli test for coverage
