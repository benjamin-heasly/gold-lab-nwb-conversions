import sys
import logging
from pathlib import Path
from contextlib import ExitStack
from argparse import ArgumentParser
from typing import Optional, Sequence

from pyramid.__about__ import __version__ as proceed_version
from pyramid.plotters.plotters import Plotter, PlotFigureController
from pyramid.neutral_zone.readers.csv import CsvNumericEventReader
from pyramid.model.numeric_events import NumericEventSource
from pyramid.trials.trials import TrialDelimiter, TrialExtractor
from pyramid.trials.trial_file import TrialFileWriter

version_string = f"Pyramid {proceed_version}"


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


def run_without_plots(trial_file: str, extractor: TrialExtractor) -> None:
    """Run without mentioning or importing matplotlib."""
    with ExitStack() as stack:
        # All these "context managers" will clean up automatically when the "with" exits.
        writer = stack.enter_context(TrialFileWriter(trial_file))
        for reader in extractor.get_readers():
            stack.enter_context(reader)

        # Extract trials indefinitely, as they come.
        while extractor.still_going():
            new_trials = extractor.read_next()
            if new_trials:
                writer.append_trials(new_trials)

        # Make a best effort to catch the last trial -- which would have no "next trial" to delimit it.
        last_trials = extractor.read_last()
        if last_trials:
            writer.append_trials([last_trials])


def run_with_plots(trial_file: str, extractor: TrialExtractor, plot_controller: PlotFigureController) -> None:
    """Run with plots, and expect to import matplotlib.
    
    This code is very similar to run_without_plots() so why is it a separate method?
    It seemed like a lot of conditional checks whether we got a plot_controller or not.
    Also, I have a hunch that it's "the right thing to do" so that we can run batch conversions
    and not have to invoke any GUI code, potentially stumbling over issues with host graphics config.
    """
    with ExitStack() as stack:
        # All these "context managers" will clean up automatically when the "with" exits.
        writer = stack.enter_context(TrialFileWriter(trial_file))
        for reader in extractor.get_readers():
            stack.enter_context(reader)
        stack.enter_context(plot_controller)

        # Extract trials indefinitely, as they come.
        while extractor.still_going() and plot_controller.get_open_figures():
            new_trials = extractor.read_next()
            if new_trials:
                writer.append_trials(new_trials)
                for trial in new_trials:
                    plot_controller.update(trial, None)

        # Make a best effort to catch the last trial -- which would have no "next trial" to delimit it.
        last_trial = extractor.read_last()
        if last_trial:
            writer.append_trials([last_trial])
            plot_controller.update(last_trial, None)


def configure_plots(plotter_paths: list[str]) -> PlotFigureController:
    if not plotter_paths:
        logging.info(f"No plotters.")
        return PlotFigureController(plotters=[])

    logging.info(f"Using {len(plotter_paths)} plotters.")
    plotters = []
    for plotter_path in plotter_paths:
        logging.info(f"  {plotter_path}")
        plotters.append(Plotter.from_dynamic_import(plotter_path))

    return PlotFigureController(plotters)


def configure_extractor(
    delimiter_csv: str,
    start_value: float,
    wrt_value: float,
    numeric_event_csvs: list[str]
) -> TrialExtractor:
    logging.info(f"Using delimiters from {delimiter_csv} start={start_value} wrt={wrt_value}")
    delimiter_reader = CsvNumericEventReader(delimiter_csv)
    delimiter_source = NumericEventSource(delimiter_reader)
    delimiter = TrialDelimiter(delimiter_source, start_value, delimiter_source, wrt_value)

    numeric_sources = {}
    if numeric_event_csvs:
        logging.info(f"Using {len(numeric_event_csvs)} extras:")
        for csv in numeric_event_csvs:
            name = Path(csv).stem
            logging.info(f"  {name}: {csv}")
            reader = CsvNumericEventReader(csv)
            source = NumericEventSource(reader)
            numeric_sources[name] = source

    return TrialExtractor(delimiter=delimiter, numeric_sources=numeric_sources)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = ArgumentParser(description="Import data and extract trials for viewing and analysis.")
    parser.add_argument("mode",
                        type=str,
                        choices=["gui", "convert"],
                        help="mode to run in: interactive gui or noninteractive convert"),
    parser.add_argument("--plotters", '-p',
                        type=str,
                        nargs="+",
                        help="TESTING: list of plotters to import and run")
    parser.add_argument("--delimiter-csv", '-d',
                        type=str,
                        help="TESTING: CSV file with trial-delimiting events")
    parser.add_argument("--start-value", '-s',
                        type=float,
                        help="TESTING: event value for delimiting trials")
    parser.add_argument("--wrt-value", '-w',
                        type=float,
                        help="TESTING: event value for trials with-respect-to times")
    parser.add_argument("--extra-csvs", '-e',
                        type=str,
                        nargs="+",
                        help="TESTING: list of CSV files with trial extra events")
    parser.add_argument("--trial-file", '-f',
                        type=str,
                        help="TESTING: JSON trial file to write")
    parser.add_argument("--version", "-v", action="version", version=version_string)

    set_up_logging()

    cli_args = parser.parse_args(argv)

    match cli_args.mode:
        case "gui":
            try:
                extractor = configure_extractor(
                    cli_args.delimiter_csv,
                    cli_args.start_value,
                    cli_args.wrt_value,
                    cli_args.extra_csvs
                )
                plot_controller = configure_plots(cli_args.plotters)
                run_with_plots(cli_args.trial_file, extractor, plot_controller)
                exit_code = 0
            except Exception:
                logging.error(f"Error running gui:", exc_info=True)
                exit_code = 1

        case "convert":
            try:
                extractor = configure_extractor(
                    cli_args.delimiter_csv,
                    cli_args.start_value,
                    cli_args.wrt_value,
                    cli_args.extra_csvs
                )
                run_without_plots(cli_args.trial_file, extractor)
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
