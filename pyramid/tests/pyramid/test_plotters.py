import sys
from pathlib import Path
from pytest import fixture

from pyramid.gui import Plotter
from pyramid.plotters.sample_plotters import SampleSinePlotter, SampleCosinePlotter

@fixture
def tests_path(request):
    this_file = Path(request.module.__file__)
    return this_file.parent


def test_installed_dynamic_import():
    #Import a plotter that was installed in the usual way (eg pip) along with pyramid itself.
    import_spec = "pyramid.plotters.sample_plotters.SampleSinePlotter"
    plotter = Plotter.from_dynamic_import(import_spec)
    assert isinstance(plotter, Plotter)
    assert isinstance(plotter, SampleSinePlotter)


def test_another_installed_dynamic_import():
    import_spec = "pyramid.plotters.sample_plotters.SampleCosinePlotter"
    plotter = Plotter.from_dynamic_import(import_spec)
    assert isinstance(plotter, Plotter)
    assert isinstance(plotter, SampleCosinePlotter)


def test_external_dynamic_import(tests_path):
    # Import a plotter from a local file that was not installed in a standard location (eg by pip).
    # We don't want to litter the sys.path, so check we cleaned up after importing.
    original_sys_path = sys.path.copy()
    plotter = Plotter.from_dynamic_import('external_package.plotter_module.ExternalSinePlotter', tests_path.as_posix())
    assert isinstance(plotter, Plotter)
    assert sys.path == original_sys_path


def test_another_external_dynamic_import(tests_path):
    original_sys_path = sys.path.copy()
    plotter = Plotter.from_dynamic_import('external_package.plotter_module.ExternalCosinePlotter', tests_path.as_posix())
    assert isinstance(plotter, Plotter)
    assert sys.path == original_sys_path
