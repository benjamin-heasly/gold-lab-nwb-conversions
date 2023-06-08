from typing import Self
from importlib import import_module
import sys

import matplotlib.pyplot as plt
from matplotlib.figure import Figure


class Plotter():
    """Abstract interface for objects that plot to a figure and update each trial."""

    def set_up(self, fig: Figure, experiment_info={}, subject_info={}) -> None:
        """Use the given fig to set up and store any axes, lines, user data, etc for this plot."""
        pass # pragma: no cover

    def update(self, fig: Figure, current_trial, trials_info, experiment_info={}, subject_info={}) -> None:
        """Update stored axes, lines, user data, etc for the current trial."""
        pass # pragma: no cover

    def clean_up(self, fig: Figure) -> None:
        """Clean up when it's time to go, if needed."""
        pass # pragma: no cover

    @classmethod
    def from_dynamic_import(cls, import_spec: str, external_package_path: str = None) -> Self:
        """Create a Plotter instance from a dynamically imported module and class.

        The given import_spec should be of the form "package.subpackage.module.ClassName".
        The "package.subpackage.module" will be imported dynamically via importlib.
        Then "ClassName" from the imported module will be invoked as a Plotter no-arg constructor.
        This should be equivalent to the static statement "from package.subpackage.module import ClassName".

        Returns a new instance of the imported Plotter class.

        Provide external_package_path in order to import a class from a module that was not
        already installed by the usual means, eg conda or pip.  The external_package_path will
        be added temporarily to the Python import search path, then removed when done here.
        """
        last_dot = import_spec.rfind(".")
        module_spec = import_spec[0:last_dot]

        try:
            original_sys_path = sys.path
            if external_package_path:
                sys.path = original_sys_path.copy()
                sys.path.append(external_package_path)
            imported_module = import_module(module_spec, package=None)
        finally:
            sys.path = original_sys_path

        class_name = import_spec[last_dot+1:]
        imported_class = getattr(imported_module, class_name)
        plotter = imported_class()
        return plotter


class PlotFigureController():
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

    def __init__(self, plotters: list[Plotter] = [], experiment_info={}, subject_info={}) -> None:
        self.plotters = plotters
        self.experiment_info = experiment_info
        self.subject_info = subject_info

    def set_up(self) -> None:
        # Use matplotlib in interactive mode instead of blocking on eg plt.show().
        plt.ion()

        # Create a managed figure for each plotter to use.
        self.figures = {plotter: plt.figure() for plotter in self.plotters}

        # Let each plotter set itself up.
        for plotter, fig in self.figures.items():
            plotter.set_up(fig, self.experiment_info, self.subject_info)

    def update(self, current_trial, trials_info) -> None:
        # Let each plotter update for the current trial.
        for plotter, fig in self.figures.items():
            if plt.fignum_exists(fig.number):
                plotter.update(fig, current_trial, trials_info, self.experiment_info, self.subject_info)
                fig.canvas.draw_idle()
                fig.canvas.flush_events()

    def clean_up(self) -> None:
        # Close each managed figure.
        for plotter, fig in self.figures.items():
            plotter.clean_up(fig)
            if plt.fignum_exists(fig.number):
                plt.close(fig)
