from pytest import raises

from pyramid.cli import main


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


def test_gui():
    cli_args = ["gui",
                "--timeout",
                "1.0",
                "--plotters",
                "pyramid.plotters.sample_plotters.SampleSinePlotter",
                "pyramid.plotters.sample_plotters.SampleCosinePlotter"
                ]
    exit_code = main(cli_args)
    assert exit_code == 0


def test_gui_no_plotters():
    cli_args = ["gui"]
    exit_code = main(cli_args)
    assert exit_code == 0


def test_convert():
    cli_args = ["convert"]
    exit_code = main(cli_args)
    assert exit_code == 1
