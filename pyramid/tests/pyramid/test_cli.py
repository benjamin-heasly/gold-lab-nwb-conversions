from pathlib import Path
import json

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


def test_gui(fixture_path, tmp_path):
    trial_file = Path(tmp_path, "trial_file.json").as_posix()
    delimiter_csv = Path(fixture_path, "delimiter.csv").as_posix()
    start_value = "1010"
    wrt_value = "42"
    foo_csv = Path(fixture_path, "foo.csv").as_posix()
    bar_csv = Path(fixture_path, "bar.csv").as_posix()

    cli_args = [
        "gui",
        "--trial-file", trial_file,
        "--delimiter-csv", delimiter_csv,
        "--start-value", start_value,
        "--wrt-value", wrt_value,
        "--extra-csvs",
        foo_csv,
        bar_csv,
        "--plotters",
        "pyramid.plotters.sample_plotters.SampleSinePlotter",
        "pyramid.plotters.sample_plotters.SampleCosinePlotter"
    ]
    exit_code = main(cli_args)
    assert exit_code == 0


def test_gui_no_plotters(fixture_path, tmp_path):
    trial_file = Path(tmp_path, "trial_file.json").as_posix()
    delimiter_csv = Path(fixture_path, "delimiter.csv").as_posix()
    start_value = "1010"
    wrt_value = "42"
    foo_csv = Path(fixture_path, "foo.csv").as_posix()
    bar_csv = Path(fixture_path, "bar.csv").as_posix()

    cli_args = [
        "gui",
        "--trial-file", trial_file,
        "--delimiter-csv", delimiter_csv,
        "--start-value", start_value,
        "--wrt-value", wrt_value,
        "--extra-csvs",
        foo_csv,
        bar_csv,
    ]
    exit_code = main(cli_args)
    assert exit_code == 0


def test_gui_plotter_error(fixture_path, tmp_path):
    trial_file = Path(tmp_path, "trial_file.json").as_posix()
    delimiter_csv = Path(fixture_path, "delimiter.csv").as_posix()
    start_value = "1010"
    wrt_value = "42"

    cli_args = [
        "gui",
        "--trial-file", trial_file,
        "--delimiter-csv", delimiter_csv,
        "--start-value", start_value,
        "--wrt-value", wrt_value,
        "--plotters", "no.such.Plotter"
    ]
    exit_code = main(cli_args)
    assert exit_code == 1


def test_convert(fixture_path, tmp_path):
    trial_file = Path(tmp_path, "trial_file.json").as_posix()
    delimiter_csv = Path(fixture_path, "delimiter.csv").as_posix()
    start_value = "1010"
    wrt_value = "42"
    foo_csv = Path(fixture_path, "foo.csv").as_posix()
    bar_csv = Path(fixture_path, "bar.csv").as_posix()
    cli_args = [
        "convert",
        "--trial-file", trial_file,
        "--delimiter-csv", delimiter_csv,
        "--start-value", start_value,
        "--wrt-value", wrt_value,
        "--extra-csvs",
        foo_csv,
        bar_csv
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
    cli_args = [
        "convert",
        "--trial-file", trial_file,
        "--delimiter-csv", "no_such_file.csv",
    ]

    exit_code = main(cli_args)
    assert exit_code == 2

    with open(trial_file) as f:
        trials = json.load(f)

    assert trials == []
