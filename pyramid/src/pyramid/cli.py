import sys
import logging
from contextlib import ExitStack
from argparse import ArgumentParser
from typing import Optional, Sequence

from pyramid.__about__ import __version__ as pyramid_version
from pyramid.config import PyramidConfig
from pyramid.neutral_zone.readers.readers import ReaderRouter
from pyramid.trials.trials import TrialDelimiter, TrialExtractor
from pyramid.trials.trial_file import TrialFileWriter
from pyramid.plotters.plotters import PlotFigureController

version_string = f"Pyramid {pyramid_version}"


def set_up_logging():
    logging.root.handlers = []
    handlers = [
        logging.StreamHandler(sys.stdout)
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers
    )
    logging.info(version_string)


def run_without_plots(
    trial_file: str,
    pyramid_config: PyramidConfig
) -> None:
    """Run without plots as fast as the data allow.

    Similar to run_with_plots(), below.
    It seemed nicer to have separate code paths, as opposed to lots of conditionals in one uber-function.
    run_without_plots() should run without touching any GUI code, avoiding potential host graphics config issues.
    """
    with ExitStack() as stack:
        # All these "context managers" will clean up automatically when the "with" exits.
        writer = stack.enter_context(TrialFileWriter(trial_file))
        for reader in pyramid_config.readers.values():
            stack.enter_context(reader)

        # Extract trials indefinitely, as they come.
        while pyramid_config.start_router.still_going():
            got_start_data = pyramid_config.start_router.route_next()
            if got_start_data:
                new_trials = pyramid_config.trial_delimiter.next()
                for new_trial in new_trials:
                    for router in pyramid_config.other_routers:
                        router.route_until(new_trial.end_time)
                        pyramid_config.trial_extractor.populate_trial(new_trial)
                    writer.append_trial(new_trial)
                    pyramid_config.trial_delimiter.discard_before(new_trial.start_time)
                    pyramid_config.trial_extractor.discard_before(new_trial.start_time)

        # Make a best effort to catch the last trial -- which would have no "next trial" to delimit it.
        pyramid_config.start_router.route_next()
        for router in pyramid_config.other_routers:
            router.route_next()
        last_trial = pyramid_config.trial_delimiter.last()
        if last_trial:
            pyramid_config.trial_extractor.populate_trial(last_trial)
            writer.append_trial(last_trial)


def run_with_plots(
    trial_file: str,
    pyramid_config: PyramidConfig
) -> None:
    """Run with plots and interactive GUI updates.

    Similar to run_without_plots(), above.
    It seemed nicer to have separate code paths, as opposed to lots of conditionals in one uber-function.
    run_without_plots() should run without touching any GUI code, avoiding potential host graphics config issues.
    """
    with ExitStack() as stack:
        # All these "context managers" will clean up automatically when the "with" exits.
        writer = stack.enter_context(TrialFileWriter(trial_file))
        for reader in pyramid_config.readers.values():
            stack.enter_context(reader)
        stack.enter_context(pyramid_config.plot_figure_controller)

        # Extract trials indefinitely, as they come.
        while pyramid_config.start_router.still_going() and pyramid_config.plot_figure_controller.get_open_figures():
            pyramid_config.plot_figure_controller.update()
            got_start_data = pyramid_config.start_router.route_next()
            if got_start_data:
                new_trials = pyramid_config.trial_delimiter.next()
                for new_trial in new_trials:
                    for router in pyramid_config.other_routers:
                        router.route_until(new_trial.end_time)
                        pyramid_config.trial_extractor.populate_trial(new_trial)
                    writer.append_trial(new_trial)
                    pyramid_config.plot_figure_controller.plot_next(
                        new_trial,
                        {"trial_count": pyramid_config.trial_delimiter.trial_count}
                    )
                    pyramid_config.trial_delimiter.discard_before(new_trial.start_time)
                    pyramid_config.trial_extractor.discard_before(new_trial.start_time)

        # Make a best effort to catch the last trial -- which would have no "next trial" to delimit it.
        pyramid_config.start_router.route_next()
        for router in pyramid_config.other_routers:
            router.route_next()
        last_trial = pyramid_config.trial_delimiter.last()
        if last_trial:
            pyramid_config.trial_extractor.populate_trial(last_trial)
            writer.append_trial(last_trial)
            pyramid_config.plot_figure_controller.plot_next(
                last_trial,
                {"trial_count": pyramid_config.trial_delimiter.trial_count}
            )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = ArgumentParser(description="Import data and extract trials for viewing and analysis.")
    parser.add_argument("mode",
                        type=str,
                        choices=["gui", "convert"],
                        help="mode to run in: interactive gui or noninteractive convert"),
    parser.add_argument("--experiment", '-e',
                        type=str,
                        help="Name of the experiment YAML file")
    parser.add_argument("--subject", '-s',
                        type=str,
                        default=None,
                        help="Name of the subject YAML file")
    parser.add_argument(
        "--readers", '-r', type=str, nargs="+",
        help="One or more reader args overrides, like: --readers reader_name.arg_name=value reader_name.arg_name=value ...")
    parser.add_argument("--trial-file", '-f',
                        type=str,
                        help="JSON trial file to write")
    parser.add_argument("--version", "-v", action="version", version=version_string)

    set_up_logging()

    cli_args = parser.parse_args(argv)

    match cli_args.mode:
        case "gui":
            try:
                pyramid_config = PyramidConfig.from_yaml_and_reader_overrides(
                    experiment_yaml=cli_args.experiment,
                    subject_yaml=cli_args.subject,
                    reader_overrides=cli_args.readers
                )
                run_with_plots(cli_args.trial_file, pyramid_config)
                exit_code = 0
            except Exception:
                logging.error(f"Error running gui:", exc_info=True)
                exit_code = 1

        case "convert":
            try:
                pyramid_config = PyramidConfig.from_yaml_and_reader_overrides(
                    experiment_yaml=cli_args.experiment,
                    subject_yaml=cli_args.subject,
                    reader_overrides=cli_args.readers
                )
                run_without_plots(cli_args.trial_file, pyramid_config)
                exit_code = 0
            except Exception:
                logging.error(f"Error running conversion:", exc_info=True)
                exit_code = 2

        case _:  # pragma: no cover
            # We don't expect this to happen -- argparse should error before we get here.
            logging.error(f"Unsupported mode: {cli_args.mode}")
            exit_code = -2

    if exit_code:
        logging.error(f"Completed with errors.")
    else:
        logging.info(f"OK.")

    return exit_code
