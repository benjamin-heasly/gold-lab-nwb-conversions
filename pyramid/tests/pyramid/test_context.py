from pathlib import Path
from pytest import fixture
import yaml
import numpy as np

from pyramid.model.model import Buffer
from pyramid.model.events import NumericEventList
from pyramid.neutral_zone.readers.readers import ReaderRoute, ReaderRouter
from pyramid.neutral_zone.readers.delay_simulator import DelaySimulatorReader
from pyramid.neutral_zone.readers.csv import CsvNumericEventReader
from pyramid.neutral_zone.transformers.standard_transformers import OffsetThenGain

from pyramid.trials.trials import TrialDelimiter, TrialExtractor

from pyramid.plotters.plotters import PlotFigureController
from pyramid.plotters.standard_plotters import BasicInfoPlotter
from pyramid.plotters.sample_plotters import SampleSinePlotter, SampleCosinePlotter

from pyramid.context import PyramidContext, configure_readers, configure_trials, configure_plotters


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


def test_configure_readers():
    readers_config = {
        "start_reader": {
            "class": "pyramid.neutral_zone.readers.csv.CsvNumericEventReader",
            "args": {
                "csv_file": "default.csv",
                "results_key": "events"
            },
            "buffers": {
                "start": {
                    "results_key": "events"
                }
            },
            "simulate_delay": True
        },
        "wrt_reader": {
            "class": "pyramid.neutral_zone.readers.csv.CsvNumericEventReader",
            "buffers": {
                "wrt": {
                    "results_key": "events"
                }
            },
        },
        "foo_reader": {
            "class": "pyramid.neutral_zone.readers.csv.CsvNumericEventReader",
            "buffers": {
                "foo": {
                    "results_key": "events"
                }
            },
        },
        "bar_reader": {
            "class": "pyramid.neutral_zone.readers.csv.CsvNumericEventReader",
            "buffers": {
                "bar": {
                    "results_key": "events"
                },
                "bar_2": {
                    "results_key": "events",
                    "transformers": [
                        {
                            "class": "pyramid.neutral_zone.transformers.standard_transformers.OffsetThenGain",
                            "args": {
                                "offset": 10,
                                "gain": -2
                            }
                        }
                    ]
                }
            },
        }
    }
    allow_simulate_delay = True
    (readers, named_buffers, reader_routers) = configure_readers(readers_config, allow_simulate_delay)

    expected_readers = {
        "start_reader": DelaySimulatorReader(CsvNumericEventReader("default.csv", "events")),
        "wrt_reader": CsvNumericEventReader(),
        "foo_reader": CsvNumericEventReader(),
        "bar_reader": CsvNumericEventReader(),
    }
    assert readers == expected_readers

    expected_named_buffers = {
        "start": Buffer(NumericEventList(np.empty([0,2]))),
        "wrt": Buffer(NumericEventList(np.empty([0,2]))),
        "foo": Buffer(NumericEventList(np.empty([0,2]))),
        "bar": Buffer(NumericEventList(np.empty([0,2]))),
        "bar_2": Buffer(NumericEventList(np.empty([0,2]))),
    }
    assert named_buffers == expected_named_buffers

    expected_reader_routers = [
        ReaderRouter(
            expected_readers["start_reader"],
            [ReaderRoute("events", "start")]
        ),
        ReaderRouter(
            expected_readers["wrt_reader"],
            [ReaderRoute("events", "wrt")]
        ),
        ReaderRouter(
            expected_readers["foo_reader"],
            [ReaderRoute("events", "foo")]
        ),
        ReaderRouter(
            expected_readers["bar_reader"],
            [
                ReaderRoute("events", "bar"),
                ReaderRoute("events", "bar_2", transformers=[OffsetThenGain(offset=10, gain=-2)])
            ]
        ),
    ]
    assert reader_routers == expected_reader_routers


def test_configure_trials():
    trials_config = {
        "start_buffer": "start",
        "start_value": 1010,
        "wrt_reader": "wrt",
        "wrt_value": 42
    }
    named_buffers = {
        "start": Buffer(NumericEventList(np.empty([0,2]))),
        "wrt": Buffer(NumericEventList(np.empty([0,2])))
    }
    (trial_delimiter, trial_extractor, start_buffer_name) = configure_trials(trials_config, named_buffers)

    expected_trial_delimiter = TrialDelimiter(named_buffers["start"], start_value=1010)
    assert trial_delimiter == expected_trial_delimiter

    expected_other_buffers = {
        name: value
        for name, value in named_buffers.items()
        if name != "start" and name != "wrt"
    }
    expected_trial_extractor = TrialExtractor(named_buffers["wrt"], wrt_value=42, named_buffers=expected_other_buffers)
    assert trial_extractor == expected_trial_extractor

    assert start_buffer_name == trials_config["start_buffer"]


def test_configure_plotters():
    plotters_config = [
        {"class": "pyramid.plotters.standard_plotters.BasicInfoPlotter"},
        {"class": "pyramid.plotters.sample_plotters.SampleSinePlotter"},
        {"class": "pyramid.plotters.sample_plotters.SampleCosinePlotter"}
    ]
    plot_figure_controller = configure_plotters(plotters_config)

    expected_plot_figure_controller = PlotFigureController(
        plotters=[BasicInfoPlotter(), SampleSinePlotter(), SampleCosinePlotter()]
    )
    assert plot_figure_controller == expected_plot_figure_controller


def test_from_yaml_and_reader_overrides(fixture_path):
    experiment_yaml = Path(fixture_path, "experiment.yaml").as_posix()
    subject_yaml = Path(fixture_path, "subject.yaml").as_posix()
    delimiter_csv = Path(fixture_path, "delimiter.csv").as_posix()

    reader_overrides = [
        f"start_reader.csv_file={delimiter_csv}"
    ]

    allow_simulate_delay = True
    context = PyramidContext.from_yaml_and_reader_overrides(
        experiment_yaml,
        subject_yaml,
        reader_overrides,
        allow_simulate_delay
    )

    with open(subject_yaml) as f:
        expected_subject = yaml.safe_load(f)

    with open(experiment_yaml) as f:
        expected_experiment = yaml.safe_load(f)

    expected_readers = {
        "start_reader": DelaySimulatorReader(CsvNumericEventReader(delimiter_csv, "events")),
        "wrt_reader": CsvNumericEventReader(),
        "foo_reader": CsvNumericEventReader(),
        "bar_reader": CsvNumericEventReader(),
    }

    expected_named_buffers = {
        "start": Buffer(NumericEventList(np.empty([0,2]))),
        "wrt": Buffer(NumericEventList(np.empty([0,2]))),
        "foo": Buffer(NumericEventList(np.empty([0,2]))),
        "bar": Buffer(NumericEventList(np.empty([0,2]))),
        "bar_2": Buffer(NumericEventList(np.empty([0,2]))),
    }

    expected_reader_routers = [
        ReaderRouter(
            expected_readers["start_reader"],
            [ReaderRoute("events", "start")]
        ),
        ReaderRouter(
            expected_readers["wrt_reader"],
            [ReaderRoute("events", "wrt")]
        ),
        ReaderRouter(
            expected_readers["foo_reader"],
            [ReaderRoute("events", "foo")]
        ),
        ReaderRouter(
            expected_readers["bar_reader"],
            [
                ReaderRoute("events", "bar"),
                ReaderRoute("events", "bar_2", transformers=[OffsetThenGain(offset=10, gain=-2)])
            ]
        ),
    ]

    expected_trial_delimiter = TrialDelimiter(expected_named_buffers["start"], start_value=1010)

    expected_other_buffers = {
        name: value
        for name, value in expected_named_buffers.items()
        if name != "start" and name != "wrt"
    }
    expected_trial_extractor = TrialExtractor(
        expected_named_buffers["wrt"],
        wrt_value=42,
        named_buffers=expected_other_buffers
    )

    expected_plot_figure_controller = PlotFigureController(
        plotters=[BasicInfoPlotter(), SampleSinePlotter(), SampleCosinePlotter()]
    )

    expected_context = PyramidContext(
        subject=expected_subject,
        experiment=expected_experiment["experiment"],
        readers=expected_readers,
        named_buffers=expected_named_buffers,
        start_router=expected_reader_routers[0],
        other_routers=expected_reader_routers[1:],
        trial_delimiter=expected_trial_delimiter,
        trial_extractor=expected_trial_extractor,
        plot_figure_controller=expected_plot_figure_controller
    )
    assert context == expected_context
