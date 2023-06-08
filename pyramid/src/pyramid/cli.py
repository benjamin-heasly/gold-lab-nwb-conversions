import sys
import logging
import time
import yaml
from argparse import ArgumentParser
from typing import Optional, Sequence

from pyramid.gui import Plotter, PlotFigureController
from pyramid.__about__ import __version__ as proceed_version


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
    controller = PlotFigureController(imported_plotters)
    controller.set_up()
    start_time = time.time()
    elapsed = 0
    while controller.get_open_figures() and elapsed < timeout:
        controller.update(None, None)
        time.sleep(0.025)
        elapsed = time.time() - start_time

    controller.clean_up()

    logging.info("Done.")
    return 0


def convert() -> int:
    logging.info("Starting noninteractive convert session.")

    logging.info("Done.")
    return 1


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
                        help="TESTING: timeout in seconds before auto-closing the gui")
    parser.add_argument("--version", "-v", action="version", version=version_string)

    set_up_logging()

    cli_args = parser.parse_args(argv)

    match cli_args.mode:
        case "gui":
            exit_code = gui(cli_args.plotters, cli_args.timeout)
        case "convert":
            exit_code = convert()
        case _:  # pragma: no cover
            # We don't expect this to happen -- argparse should error before we get here.
            logging.error(f"Unsupported mode: {cli_args.mode}")
            exit_code = -2

    if exit_code:
        logging.error(f"Completed with errors.")
    else:
        logging.info(f"OK.")

    return exit_code
