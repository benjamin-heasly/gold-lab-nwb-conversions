from pathlib import Path
import copy
import json
import yaml

from pytest import raises, fixture

from pyramid.cli import main


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


def test_help():
    with raises(SystemExit) as exception_info:
        main(["--help"])
    assert 0 in exception_info.value.args


def test_mode_required():
    with raises(SystemExit) as exception_info:
        main([])
    assert 2 in exception_info.value.args


def test_invalid_input():
    with raises(SystemExit) as exception_info:
        main(["invalid!"])
    assert 2 in exception_info.value.args


experiment_config = {
    "experiment": {
        "experimenter": ["Last, First M", "Last, First Middle"],
        "experiment_description": "A test experiment.",
        "institution": "University of Fiction",
        "lab": "The Fiction Lab",
        "keywords": ["fictional", "test"]
    },
    "readers": {
        "delimiter_reader": {
            "class": "pyramid.neutral_zone.readers.csv.CsvNumericEventReader",
            "buffers": {
                "start": {"results_key": "events"},
                "wrt": {"results_key": "events"},
            }
        },
        "foo_reader": {
            "class": "pyramid.neutral_zone.readers.csv.CsvNumericEventReader",
            "buffers": {
                "foo": {"results_key": "events"},
            }
        },
        "bar_reader": {
            "class": "pyramid.neutral_zone.readers.csv.CsvNumericEventReader",
            "buffers": {
                "bar": {"results_key": "events"},
                "bar_2": {
                    "results_key": "events",
                    "transformers": [
                      {
                          "class": "pyramid.neutral_zone.transformers.standard_transformers.OffsetThenGain",
                          "args": {"offset": 10, "gain": -2}
                      }
                    ]
                },
            }
        },
        "match_trial_signal_reader": {
            "class": "pyramid.neutral_zone.readers.csv.CsvSignalReader",
            "args": {
                "sample_frequency": 10,
                "lines_per_chunk": 3
            },
            "buffers": {
                "match_trial_signal": {"results_key": "samples"},
            }
        },
    },
    "trials": {
        "start_buffer": "start",
        "start_value": 1010,
        "wrt_buffer": "wrt",
        "wrt_value": 42,
        "enhancers": [
            {"class": "pyramid.trials.standard_enhancers.TrialDurationEnhancer"}
        ]
    },
    "plotters": [
        {"class": "pyramid.plotters.standard_plotters.SignalChunksPlotter"},
        {"class": "pyramid.plotters.standard_plotters.SignalChunksPlotter", "args": {"channel_ids": ["no_match"]}},
        {"class": "pyramid.plotters.standard_plotters.NumericEventsPlotter"},
        {"class": "pyramid.plotters.standard_plotters.BasicInfoPlotter"},
    ]
}


def test_gui_success(fixture_path, tmp_path):
    delimiter_csv = Path(fixture_path, "delimiter.csv").as_posix()
    foo_csv = Path(fixture_path, "foo.csv").as_posix()
    bar_csv = Path(fixture_path, "bar.csv").as_posix()
    signal_csv = Path(fixture_path, "match_trial_signal.csv").as_posix()
    subject_yaml = Path(fixture_path, "subject.yaml").as_posix()
    trial_file = Path(tmp_path, "trial_file.json").as_posix()
    experiment_yaml = Path(tmp_path, "experiment.yaml").as_posix()

    with open(experiment_yaml, "w") as f:
        yaml.safe_dump(experiment_config, f)

    cli_args = [
        "gui",
        "--trial-file", trial_file,
        "--experiment", experiment_yaml,
        "--subject", subject_yaml,
        "--readers",
        f"delimiter_reader.csv_file={delimiter_csv}",
        f"foo_reader.csv_file={foo_csv}",
        f"bar_reader.csv_file={bar_csv}",
        f"match_trial_signal_reader.csv_file={signal_csv}"
    ]
    exit_code = main(cli_args)
    assert exit_code == 0


def test_gui_no_plotters(fixture_path, tmp_path):
    delimiter_csv = Path(fixture_path, "delimiter.csv").as_posix()
    foo_csv = Path(fixture_path, "foo.csv").as_posix()
    bar_csv = Path(fixture_path, "bar.csv").as_posix()
    signal_csv = Path(fixture_path, "match_trial_signal.csv").as_posix()
    subject_yaml = Path(fixture_path, "subject.yaml").as_posix()
    trial_file = Path(tmp_path, "trial_file.json").as_posix()
    experiment_yaml = Path(tmp_path, "experiment.yaml").as_posix()

    no_plotters_config = {
        "readers": experiment_config["readers"],
        "trials": experiment_config["trials"]
    }

    with open(experiment_yaml, "w") as f:
        yaml.safe_dump(no_plotters_config, f)

    cli_args = [
        "gui",
        "--trial-file", trial_file,
        "--experiment", experiment_yaml,
        "--subject", subject_yaml,
        "--readers",
        f"delimiter_reader.csv_file={delimiter_csv}",
        f"foo_reader.csv_file={foo_csv}",
        f"bar_reader.csv_file={bar_csv}",
        f"match_trial_signal_reader.csv_file={signal_csv}"
    ]
    exit_code = main(cli_args)
    assert exit_code == 0


def test_gui_simulate_delay(fixture_path, tmp_path):
    delimiter_csv = Path(fixture_path, "delimiter.csv").as_posix()
    foo_csv = Path(fixture_path, "foo.csv").as_posix()
    bar_csv = Path(fixture_path, "bar.csv").as_posix()
    signal_csv = Path(fixture_path, "match_trial_signal.csv").as_posix()
    subject_yaml = Path(fixture_path, "subject.yaml").as_posix()
    trial_file = Path(tmp_path, "trial_file.json").as_posix()
    experiment_yaml = Path(tmp_path, "experiment.yaml").as_posix()

    simulate_delay_config = copy.deepcopy(experiment_config)
    simulate_delay_config["readers"]["delimiter_reader"]["simulate_delay"] = True

    with open(experiment_yaml, "w") as f:
        yaml.safe_dump(simulate_delay_config, f)

    cli_args = [
        "gui",
        "--trial-file", trial_file,
        "--experiment", experiment_yaml,
        "--subject", subject_yaml,
        "--readers",
        f"delimiter_reader.csv_file={delimiter_csv}",
        f"foo_reader.csv_file={foo_csv}",
        f"bar_reader.csv_file={bar_csv}",
        f"match_trial_signal_reader.csv_file={signal_csv}"
    ]
    exit_code = main(cli_args)
    assert exit_code == 0


def test_gui_plotter_error(fixture_path, tmp_path):
    delimiter_csv = Path(fixture_path, "delimiter.csv").as_posix()
    foo_csv = Path(fixture_path, "foo.csv").as_posix()
    bar_csv = Path(fixture_path, "bar.csv").as_posix()
    signal_csv = Path(fixture_path, "match_trial_signal.csv").as_posix()
    subject_yaml = Path(fixture_path, "subject.yaml").as_posix()
    trial_file = Path(tmp_path, "trial_file.json").as_posix()
    experiment_yaml = Path(tmp_path, "experiment.yaml").as_posix()

    error_plotters_config = {
        "readers": experiment_config["readers"],
        "trials": experiment_config["trials"],
        "plotters": [
            {"class": "no.such.Plotter"},
        ]
    }

    with open(experiment_yaml, "w") as f:
        yaml.safe_dump(error_plotters_config, f)

    cli_args = [
        "gui",
        "--trial-file", trial_file,
        "--experiment", experiment_yaml,
        "--subject", subject_yaml,
        "--readers",
        f"delimiter_reader.csv_file={delimiter_csv}",
        f"foo_reader.csv_file={foo_csv}",
        f"bar_reader.csv_file={bar_csv}",
        f"match_trial_signal_reader.csv_file={signal_csv}"
    ]
    exit_code = main(cli_args)
    assert exit_code == 1


def test_convert(fixture_path, tmp_path):
    delimiter_csv = Path(fixture_path, "delimiter.csv").as_posix()
    foo_csv = Path(fixture_path, "foo.csv").as_posix()
    bar_csv = Path(fixture_path, "bar.csv").as_posix()
    signal_csv = Path(fixture_path, "match_trial_signal.csv").as_posix()
    subject_yaml = Path(fixture_path, "subject.yaml").as_posix()
    trial_file = Path(tmp_path, "trial_file.json").as_posix()
    experiment_yaml = Path(tmp_path, "experiment.yaml").as_posix()

    with open(experiment_yaml, "w") as f:
        yaml.safe_dump(experiment_config, f)

    cli_args = [
        "convert",
        "--trial-file", trial_file,
        "--experiment", experiment_yaml,
        "--subject", subject_yaml,
        "--readers",
        f"delimiter_reader.csv_file={delimiter_csv}",
        f"foo_reader.csv_file={foo_csv}",
        f"bar_reader.csv_file={bar_csv}",
        f"match_trial_signal_reader.csv_file={signal_csv}"
    ]
    exit_code = main(cli_args)
    assert exit_code == 0

    with open(trial_file) as f:
        trials = json.load(f)

    expected_trial_file = Path(fixture_path, "expected_trial_file.json")
    with open(expected_trial_file) as f:
        expected_trials = json.load(f)

    assert trials == expected_trials


def test_convert_error(tmp_path):
    trial_file = Path(tmp_path, "trial_file.json").as_posix()
    experiment_yaml = Path(tmp_path, "experiment.yaml").as_posix()

    with open(experiment_yaml, "w") as f:
        yaml.safe_dump(experiment_config, f)

    cli_args = [
        "convert",
        "--trial-file", trial_file,
        "--experiment", experiment_yaml,
        "--readers",
        "delimiter_reader.csv_file=no_such_file.csv",
        "foo_reader.csv_file=no_such_file.csv",
        "bar_reader.csv_file=no_such_file.csv"
    ]
    exit_code = main(cli_args)
    assert exit_code == 2

    with open(trial_file) as f:
        trials = json.load(f)

    assert trials == []


def test_graph(tmp_path):
    experiment_yaml = Path(tmp_path, "experiment.yaml").as_posix()
    graph_file = Path(tmp_path, "graph.png").as_posix()

    with open(experiment_yaml, "w") as f:
        yaml.safe_dump(experiment_config, f)

    cli_args = [
        "graph",
        "--graph-file", graph_file,
        "--experiment", experiment_yaml
    ]
    exit_code = main(cli_args)
    assert exit_code == 0

    assert Path(graph_file).exists()
    assert Path(tmp_path, "graph.dot").exists()


def test_graph_error(tmp_path):
    graph_file = Path(tmp_path, "graph.png").as_posix()

    cli_args = [
        "graph",
        "--graph-file", graph_file,
        "--experiment", "no_such_experiment.yaml"
    ]
    exit_code = main(cli_args)
    assert exit_code == 2

    assert not Path(graph_file).exists()
    assert not Path(tmp_path, "graph.dot").exists()
