from types import TracebackType
from typing import Self, Any, ContextManager

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pyramid.model.model import DynamicImport
from pyramid.trials.trials import Trial


class Plotter(DynamicImport):
    """Abstract interface for objects that plot to a figure and update each trial."""

    def set_up(
        self,
        fig: Figure,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        """Use the given fig to set up and store any axes, lines, user data, etc for this plot."""
        pass # pragma: no cover

    def update(
        self,
        fig: Figure,
        current_trial: Trial,
        trial_count: int,
        experiment_info: dict[str: Any],
        subject_info: dict[str: Any]
    ) -> None:
        """Update stored axes, lines, user data, etc for the current trial."""
        pass # pragma: no cover

    def clean_up(self, fig: Figure) -> None:
        """Clean up when it's time to go, if needed."""
        pass # pragma: no cover


class PlotFigureController(ContextManager):
    """Registry and utils for Plotter instances and corresponding, managed figures.

    We want pyramid GUI mode to be able to juggle several tasks at the same time:
     - checking for new trial updates
     - updating plots for each new trial
     - responding to GUI user inputs like resizing figures or pressing buttons/widgets
     - responding to GUI window closing so we can exit

    So, things are asyncronous from the trial data side, and from the user interface side.
    This is manageable, but not automatically.
    Here's some reading that informed the approach used here:
     - https://matplotlib.org/stable/users/explain/interactive_guide.html#explicitly-spinning-the-event-loop
     - https://stackoverflow.com/questions/7557098/matplotlib-interactive-mode-determine-if-figure-window-is-still-displayed

    We'll expect the pyramid GUI runner to loop through these tasks.
    It will expect the data side to poll for data or block with a short timeout.
    This will allow us to interleave GUI updates and event processing as well.

    This class implementes the GUI updates and event processing part.
    """

    def __init__(
        self,
        plotters: list[Plotter] = [],
        experiment_info: dict[str, Any] = {},
        subject_info: dict[str, Any] = {}
    ) -> None:
        self.plotters = plotters
        self.experiment_info = experiment_info
        self.subject_info = subject_info
        self.figures = {}

    def __eq__(self, other: object) -> bool:
        """Compare controllers field-wise, to support use of this class in tests."""
        if isinstance(other, self.__class__):
            plotter_counts_equal = len(self.plotters) == len(other.plotters)
            plotter_types_equal = [isinstance(a, b.__class__) for a, b in zip(self.plotters, other.plotters)]
            return (
                plotter_counts_equal
                and all(plotter_types_equal)
                and self.experiment_info == other.experiment_info
                and self.subject_info == other.subject_info
            )
        else:  # pragma: no cover
            return False

    def __enter__(self) -> Self:
        # Use matplotlib in interactive mode instead of blocking on eg plt.show().
        plt.ion()

        # Create a managed figure for each plotter to use.
        self.figures = {plotter: plt.figure() for plotter in self.plotters}

        # Let each plotter set itself up.
        for plotter, fig in self.figures.items():
            plotter.set_up(fig, self.experiment_info, self.subject_info)

        return self

    def plot_next(self, current_trial: Trial, trial_count: int) -> None:
        # Let each plotter update for the current trial.
        for plotter, fig in self.figures.items():
            if plt.fignum_exists(fig.number):
                plotter.update(fig, current_trial, trial_count, self.experiment_info, self.subject_info)

    def update(self) -> None:
        for fig in self.figures.values():
            if plt.fignum_exists(fig.number):
                fig.canvas.draw_idle()
                fig.canvas.flush_events()

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None
    ) -> bool | None:
        # Close each managed figure.
        for plotter, fig in self.figures.items():
            plotter.clean_up(fig)
            if plt.fignum_exists(fig.number):
                plt.close(fig)

    def get_open_figures(self) -> list[Figure]:
        return [figure for figure in self.figures.values() if plt.fignum_exists(figure.number)]
