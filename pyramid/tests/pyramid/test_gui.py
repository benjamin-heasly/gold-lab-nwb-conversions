from pyramid.gui import Plotter
from pyramid.plotters.sample_plotters import SampleSinePlotter, SampleCosinePlotter


def test_installed_dynamic_import():
    import_spec = "pyramid.plotters.sample_plotters.SampleSinePlotter"
    plotter = Plotter.from_dynamic_import(import_spec)
    assert isinstance(plotter, Plotter)
    assert isinstance(plotter, SampleSinePlotter)


def test_another_installed_dynamic_import():
    import_spec = "pyramid.plotters.sample_plotters.SampleCosinePlotter"
    plotter = Plotter.from_dynamic_import(import_spec)
    assert isinstance(plotter, Plotter)
    assert isinstance(plotter, SampleCosinePlotter)
