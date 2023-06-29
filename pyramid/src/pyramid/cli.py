import sys
import logging
from argparse import ArgumentParser
from typing import Optional, Sequence

from pyramid.__about__ import __version__ as pyramid_version
from pyramid.context import PyramidContext

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
    parser.add_argument("--readers",
                        '-r',
                        type=str,
                        nargs="+",
                        help="Reader args eg: --readers reader_name.arg_name=value reader_name.arg_name=value ...")
    parser.add_argument("--trial-file", '-f',
                        type=str,
                        help="JSON trial file to write")
    parser.add_argument("--version", "-v",
                        action="version",
                        version=version_string)

    set_up_logging()

    cli_args = parser.parse_args(argv)

    match cli_args.mode:
        case "gui":
            try:
                context = PyramidContext.from_yaml_and_reader_overrides(
                    experiment_yaml=cli_args.experiment,
                    subject_yaml=cli_args.subject,
                    reader_overrides=cli_args.readers,
                    allow_simulate_delay=True
                )
                context.run_with_plots(cli_args.trial_file)
                exit_code = 0
            except Exception:
                logging.error(f"Error running gui:", exc_info=True)
                exit_code = 1

        case "convert":
            try:
                context = PyramidContext.from_yaml_and_reader_overrides(
                    experiment_yaml=cli_args.experiment,
                    subject_yaml=cli_args.subject,
                    reader_overrides=cli_args.readers
                )
                context.run_without_plots(cli_args.trial_file)
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
