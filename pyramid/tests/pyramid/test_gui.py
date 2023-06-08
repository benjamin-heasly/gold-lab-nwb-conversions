import sys
from pathlib import Path
from pytest import fixture
import matplotlib.pyplot as plt

from pyramid.gui import Plotter, PlotFigureController
from pyramid.plotters.sample_plotters import SampleSinePlotter, SampleCosinePlotter


@fixture
def tests_path(request):
    this_file = Path(request.module.__file__)
    return this_file.parent


def test_installed_plotter_dynamic_import():
    # Import a plotter that was installed in the usual way (eg by pip) along with pyramid itself.
    import_spec = "pyramid.plotters.sample_plotters.SampleSinePlotter"
    plotter = Plotter.from_dynamic_import(import_spec)
    assert isinstance(plotter, Plotter)
    assert isinstance(plotter, SampleSinePlotter)


def test_another_installed_plotter_dynamic_import():
    import_spec = "pyramid.plotters.sample_plotters.SampleCosinePlotter"
    plotter = Plotter.from_dynamic_import(import_spec)
    assert isinstance(plotter, Plotter)
    assert isinstance(plotter, SampleCosinePlotter)


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
    plotter = SampleSinePlotter()
    controller = PlotFigureController(plotters=[plotter])
    controller.set_up()
    assert len(controller.get_open_figures()) == 1
    assert plotter.update_count == 0

    controller.update(None, None)
    assert plotter.update_count == 1

    controller.update(None, None)
    assert plotter.update_count == 2

    controller.clean_up()
    assert plotter.update_count == -1
    assert len(controller.get_open_figures()) == 0


def test_multiple_figures():
    plotters = [SampleSinePlotter(), SampleCosinePlotter(), SampleSinePlotter()]
    controller = PlotFigureController(plotters=plotters)
    controller.set_up()
    assert len(controller.get_open_figures()) == len(plotters)
    for plotter in plotters:
        assert plotter.update_count == 0

    controller.update(None, None)
    for plotter in plotters:
        assert plotter.update_count == 1

    controller.update(None, None)
    for plotter in plotters:
        assert plotter.update_count == 2

    controller.clean_up()
    for plotter in plotters:
        assert plotter.update_count == -1
    assert len(controller.get_open_figures()) == 0


def test_close_figure_early():
    plotters = [SampleSinePlotter(), SampleCosinePlotter(), SampleSinePlotter()]
    controller = PlotFigureController(plotters=plotters)
    controller.set_up()
    assert len(controller.get_open_figures()) == len(plotters)
    for plotter in plotters:
        assert plotter.update_count == 0

    controller.update(None, None)
    for plotter in plotters:
        assert plotter.update_count == 1

    # As if user closed a figure unexpectedly.
    victim_figure = controller.figures[plotters[1]]
    plt.close(victim_figure)
    assert len(controller.get_open_figures()) == len(plotters) - 1

    controller.update(None, None)
    assert len(controller.get_open_figures()) == len(plotters) - 1
    assert plotters[0].update_count == 2
    assert plotters[1].update_count == 1
    assert plotters[2].update_count == 2

    controller.clean_up()
    for plotter in plotters:
        assert plotter.update_count == -1
    assert len(controller.get_open_figures()) == 0
