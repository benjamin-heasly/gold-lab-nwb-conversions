import sys
from pathlib import Path
from pytest import fixture
import matplotlib.pyplot as plt

from pyramid.trials.trials import Trial
from pyramid.plotters.plotters import Plotter, PlotFigureController
from pyramid.plotters.standard_plotters import NumericEventsPlotter, SignalChunksPlotter


@fixture
def tests_path(request):
    this_file = Path(request.module.__file__)
    return this_file.parent


def test_installed_plotter_dynamic_import():
    # Import a plotter that was installed in the usual way (eg by pip) along with pyramid itself.
    import_spec = "pyramid.plotters.standard_plotters.NumericEventsPlotter"
    plotter = Plotter.from_dynamic_import(import_spec)
    assert isinstance(plotter, Plotter)
    assert isinstance(plotter, NumericEventsPlotter)


def test_another_installed_plotter_dynamic_import():
    import_spec = "pyramid.plotters.standard_plotters.SignalChunksPlotter"
    plotter = Plotter.from_dynamic_import(import_spec)
    assert isinstance(plotter, Plotter)
    assert isinstance(plotter, SignalChunksPlotter)


def test_external_plotter_dynamic_import(tests_path):
    # Import a plotter from a local file that was not installed in a standard location (eg by pip).
    # We don't want to litter the sys.path, so check we cleaned up after importing.
    original_sys_path = sys.path.copy()
    plotter = Plotter.from_dynamic_import('external_package.plotter_module.ExternalPlotter1', tests_path.as_posix())
    assert isinstance(plotter, Plotter)
    assert sys.path == original_sys_path


def test_another_external_plotter_dynamic_import(tests_path):
    original_sys_path = sys.path.copy()
    plotter = Plotter.from_dynamic_import('external_package.plotter_module.ExternalPlotter2', tests_path.as_posix())
    assert isinstance(plotter, Plotter)
    assert sys.path == original_sys_path


def test_single_figure():
    trial = Trial(0.0, 1.0)
    plotter = NumericEventsPlotter()
    with PlotFigureController(plotters=[plotter]) as controller:
        assert len(controller.get_open_figures()) == 1
        assert len(plotter.history) == 0

        controller.plot_next(trial, None)
        assert len(plotter.history) == 1

        controller.plot_next(trial, None)
        assert len(plotter.history) == 2

    assert len(plotter.history) == 0
    assert len(controller.get_open_figures()) == 0


def test_multiple_figures():
    trial = Trial(0.0, 1.0)
    plotters = [NumericEventsPlotter(), SignalChunksPlotter(), NumericEventsPlotter()]
    with PlotFigureController(plotters) as controller:
        assert len(controller.get_open_figures()) == len(plotters)
        for plotter in plotters:
            assert len(plotter.history) == 0

        controller.plot_next(trial, None)
        for plotter in plotters:
            assert len(plotter.history) == 1

        controller.plot_next(trial, None)
        for plotter in plotters:
            assert len(plotter.history) == 2

    for plotter in plotters:
        assert len(plotter.history) == 0
    assert len(controller.get_open_figures()) == 0


def test_close_figure_early():
    trial = Trial(0.0, 1.0)
    plotters = [NumericEventsPlotter(), SignalChunksPlotter(), NumericEventsPlotter()]
    with PlotFigureController(plotters) as controller:
        assert len(controller.get_open_figures()) == len(plotters)
        for plotter in plotters:
            assert len(plotter.history) == 0

        controller.plot_next(trial, None)
        for plotter in plotters:
            assert len(plotter.history) == 1

        # As if user closed a figure unexpectedly.
        victim_figure = controller.figures[plotters[1]]
        plt.close(victim_figure)
        assert len(controller.get_open_figures()) == len(plotters) - 1

        controller.plot_next(trial, None)
        assert len(controller.get_open_figures()) == len(plotters) - 1
        assert len(plotters[0].history) == 2
        assert len(plotters[1].history) == 1
        assert len(plotters[2].history) == 2

    for plotter in plotters:
        assert len(plotter.history) == 0
    assert len(controller.get_open_figures()) == 0
