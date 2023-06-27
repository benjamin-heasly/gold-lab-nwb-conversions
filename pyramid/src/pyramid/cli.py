import sys
import logging
from pathlib import Path
from contextlib import ExitStack
from argparse import ArgumentParser
from typing import Optional, Sequence

from pyramid.__about__ import __version__ as proceed_version
from pyramid.neutral_zone.readers.readers import ReaderRoute, ReaderRouter
from pyramid.neutral_zone.readers.csv import CsvNumericEventReader
from pyramid.neutral_zone.readers.delay_simulator import DelaySimulatorReader
from pyramid.model.numeric_events import NumericEventBuffer
from pyramid.trials.trials import TrialDelimiter, TrialExtractor
from pyramid.trials.trial_file import TrialFileWriter
from pyramid.plotters.plotters import Plotter, PlotFigureController

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


def run_without_plots(
    trial_file: str,
    delimiter: TrialDelimiter,
    extractor: TrialExtractor,
    routers: list[ReaderRouter]
) -> None:
    """Run without plots as fast as the data allow.
    
    Similar to run_with_plots(), below.
    It seemed nicer to have separate code paths, as opposed to lots of conditionals in one uber-function.
    run_without_plots() should run without touching any GUI code, avoiding potential host graphics config issues.
    """
    with ExitStack() as stack:
        # All these "context managers" will clean up automatically when the "with" exits.
        writer = stack.enter_context(TrialFileWriter(trial_file))
        for router in routers:
            stack.enter_context(router.reader)

        # Extract trials indefinitely, as they come.
        start_router = routers[0]
        other_routers = routers[1:]
        while start_router.still_going():
            got_start_data = start_router.route_next()
            if got_start_data:
                new_trials = delimiter.next()
                for new_trial in new_trials:
                    for router in other_routers:
                        router.route_until(new_trial.end_time)
                        extractor.populate_trial(new_trial)
                    writer.append_trial(new_trial)
                    delimiter.discard_before(new_trial.start_time)
                    extractor.discard_before(new_trial.start_time)

        # Make a best effort to catch the last trial -- which would have no "next trial" to delimit it.
        for router in routers:
            router.route_next()
        last_trial = delimiter.last()
        if last_trial:
            extractor.populate_trial(last_trial)
            writer.append_trial(last_trial)


def run_with_plots(
        trial_file: str,
        delimiter: TrialDelimiter,
        extractor: TrialExtractor,
        routers: list[ReaderRouter],
        plot_controller: PlotFigureController
) -> None:
    """Run with plots and interactive GUI updates.

    Similar to run_without_plots(), above.
    It seemed nicer to have separate code paths, as opposed to lots of conditionals in one uber-function.
    run_without_plots() should run without touching any GUI code, avoiding potential host graphics config issues.
    """
    with ExitStack() as stack:
        # All these "context managers" will clean up automatically when the "with" exits.
        writer = stack.enter_context(TrialFileWriter(trial_file))
        for router in routers:
            stack.enter_context(router.reader)
        stack.enter_context(plot_controller)

        # Extract trials indefinitely, as they come.
        start_router = routers[0]
        other_routers = routers[1:]
        while start_router.still_going() and plot_controller.get_open_figures():
            plot_controller.update()
            got_start_data = start_router.route_next()
            if got_start_data:
                new_trials = delimiter.next()
                for new_trial in new_trials:
                    for router in other_routers:
                        router.route_until(new_trial.end_time)
                        extractor.populate_trial(new_trial)
                    writer.append_trial(new_trial)
                    plot_controller.plot_next(new_trial, {"trial_count": delimiter.trial_count})
                    delimiter.discard_before(new_trial.start_time)
                    extractor.discard_before(new_trial.start_time)

        # Make a best effort to catch the last trial -- which would have no "next trial" to delimit it.
        for router in routers:
            router.route_next()
        last_trial = delimiter.last()
        if last_trial:
            extractor.populate_trial(last_trial)
            writer.append_trial(last_trial)
            plot_controller.plot_next(last_trial, {"trial_count": delimiter.trial_count})


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


def configure_conversion(
    delimiter_csv: str,
    start_value: float,
    wrt_value: float,
    numeric_event_csvs: list[str],
    simulate_delay: bool = False
) -> tuple[TrialDelimiter, TrialExtractor, list[ReaderRouter]]:
    logging.info(f"Using delimiters from {delimiter_csv} start={start_value} wrt={wrt_value}")
    if simulate_delay:
        delimiter_reader = DelaySimulatorReader(CsvNumericEventReader(delimiter_csv, results_name="delimiters"))
    else:
        delimiter_reader = CsvNumericEventReader(delimiter_csv, results_name="delimiters")
    start_buffer = NumericEventBuffer()
    start_route = ReaderRoute("delimiters", "start")
    wrt_buffer = NumericEventBuffer()
    wrt_route = ReaderRoute("delimiters", "wrt")
    delimiter_router = ReaderRouter(delimiter_reader, {"start": start_buffer, "wrt": wrt_buffer}, [start_route, wrt_route])
    delimiter = TrialDelimiter(start_buffer, start_value)

    routers = [delimiter_router]

    extra_buffers = {}
    if numeric_event_csvs:
        logging.info(f"Using {len(numeric_event_csvs)} extras:")
        for csv in numeric_event_csvs:
            name = Path(csv).stem
            logging.info(f"  {name}: {csv}")
            reader = CsvNumericEventReader(csv, results_name=name)
            buffer = NumericEventBuffer()
            route = ReaderRoute(name, name)
            router = ReaderRouter(reader, {name: buffer}, [route])
            extra_buffers[name] = buffer
            routers.append(router)

    extractor = TrialExtractor(
        wrt_buffer=wrt_buffer,
        wrt_value=wrt_value,
        named_buffers=extra_buffers
    )

    return (delimiter, extractor, routers)


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
    parser.add_argument("--simulate-delay", '-D',
                        action='store_true',
                        help="TESTING: simulate delay between trial delimiter events")
    parser.add_argument("--version", "-v", action="version", version=version_string)

    set_up_logging()

    cli_args = parser.parse_args(argv)

    match cli_args.mode:
        case "gui":
            try:
                (delimiter, extractor, routers) = configure_conversion(
                    cli_args.delimiter_csv,
                    cli_args.start_value,
                    cli_args.wrt_value,
                    cli_args.extra_csvs,
                    cli_args.simulate_delay
                )
                plot_controller = configure_plots(cli_args.plotters)
                run_with_plots(cli_args.trial_file, delimiter, extractor, routers, plot_controller)
                exit_code = 0
            except Exception:
                logging.error(f"Error running gui:", exc_info=True)
                exit_code = 1

        case "convert":
            try:
                (delimiter, extractor, routers) = configure_conversion(
                    cli_args.delimiter_csv,
                    cli_args.start_value,
                    cli_args.wrt_value,
                    cli_args.extra_csvs,
                    cli_args.simulate_delay
                )
                run_without_plots(cli_args.trial_file, delimiter, extractor, routers)
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
