import sys
import logging
import time
from pathlib import Path
from contextlib import ExitStack
import yaml
from argparse import ArgumentParser
from typing import Optional, Sequence

from pyramid.__about__ import __version__ as proceed_version
from pyramid.gui import Plotter, PlotFigureController
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


def gui(plotters: list[str], timeout: float = 60.0) -> int:
    logging.info("Starting interactive gui session.")

    if not plotters:
        logging.info(f"No plotters.")
        return 0

    logging.info(f"Using {len(plotters)} plotters.")
    for plotter in plotters:
        logging.info(f"  {plotter}")

    imported_plotters = [Plotter.from_dynamic_import(plotter) for plotter in plotters]
    with PlotFigureController(imported_plotters) as controller:
        start_time = time.time()
        elapsed = 0
        while controller.get_open_figures() and elapsed < timeout:
            controller.update(None, None)
            time.sleep(0.025)
            elapsed = time.time() - start_time

    logging.info("Done.")
    return 0


def convert(trial_file: str, delimiter_csv: str, start_value: float, wrt_value: float, extra_csvs: list[str]) -> int:
    logging.info("Starting noninteractive convert session.")
    logging.info(f"Using delimiters from {delimiter_csv} start={start_value} wrt={wrt_value}")

    if extra_csvs:
        logging.info(f"Using {len(extra_csvs)} extras:")
        for extra in extra_csvs:
            name = Path(extra).stem
            logging.info(f"  {name}: {extra}")

    logging.info(f"Writing to trial file {trial_file}")

    delimiter_reader = CsvNumericEventReader(delimiter_csv)
    delimiter_source = NumericEventSource(delimiter_reader)
    delimiter = TrialDelimiter(delimiter_source, start_value, delimiter_source, wrt_value)

    numeric_sources = {}
    for extra in extra_csvs:
        name = Path(extra).stem
        reader = CsvNumericEventReader(extra)
        source = NumericEventSource(reader)
        numeric_sources[name] = source

    extractor = TrialExtractor(delimiter=delimiter, numeric_sources=numeric_sources)

    with ExitStack() as stack:
        stack.enter_context(delimiter_reader)
        for source in numeric_sources.values():
            stack.enter_context(source.reader)
        writer = stack.enter_context(TrialFileWriter(trial_file))

        try:
            while delimiter_source.reader_exception is None:
                new_trials = extractor.read_next()
                if new_trials:
                    logging.info(f"Got new trials: {new_trials}")
                    writer.append_trials(new_trials)
        except Exception as e:
            logging.info(f"I think we're done.", exc_info=True)

        last_trials = extractor.read_last()
        if last_trials:
            logging.info(f"Got last trials: {last_trials}")
            writer.append_trials([last_trials])

    logging.info("Done.")
    return 0


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
    parser.add_argument("--timeout", '-t',
                        type=float,
                        default=10,
                        help="TESTING: timeout in seconds before auto-closing the gui")
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
            exit_code = gui(cli_args.plotters, cli_args.timeout)
        case "convert":
            exit_code = convert(cli_args.trial_file, cli_args.delimiter_csv,
                                cli_args.start_value, cli_args.wrt_value, cli_args.extra_csvs)
        case _:  # pragma: no cover
            # We don't expect this to happen -- argparse should error before we get here.
            logging.error(f"Unsupported mode: {cli_args.mode}")
            exit_code = -2

    if exit_code:
        logging.error(f"Completed with errors.")
    else:
        logging.info(f"OK.")

    return exit_code
