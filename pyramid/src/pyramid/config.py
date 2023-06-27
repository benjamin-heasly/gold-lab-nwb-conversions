from typing import Any, Self
import logging
from pathlib import Path
from dataclasses import dataclass

from pyramid.neutral_zone.readers.readers import Reader, ReaderRoute, ReaderRouter
from pyramid.neutral_zone.readers.csv import CsvNumericEventReader
from pyramid.neutral_zone.readers.delay_simulator import DelaySimulatorReader
from pyramid.model.numeric_events import NumericEventBuffer
from pyramid.trials.trials import TrialDelimiter, TrialExtractor
from pyramid.plotters.plotters import Plotter, PlotFigureController


@dataclass
class PyramidConfig():
    subject: dict[str, Any]
    experiment: dict[str, Any]
    readers: dict[str, Reader]
    named_buffers: dict[str, NumericEventBuffer]
    reader_routers: list[ReaderRouter]
    trial_delimiter: TrialDelimiter
    trial_extractor: TrialExtractor
    plot_figure_controller: PlotFigureController

    def to_graphviz(self):
        pass

    @classmethod
    def from_yaml_and_overrides(cls, yaml_file: str, overrides: dict[str, ]) -> Self:
        # read yaml to dict
        # apply "readers" overrides to reader args
        # then from_dict with all that
        pass

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> Self:
        subject = config.get("subject", {})
        experiment = config.get("experiment", {})
        readers = configure_readers(config["readers"])
        (named_buffers, reader_routers) = configure_buffers(config["buffers"])
        (trial_delimiter, trial_extractor) = configure_trials(config["trials"], named_buffers)
        plot_figure_controller = configure_plotters(config.get("plotters", []))


def configure_readers(reader_config: dict[str, dict]) -> dict[str, Reader]:
    pass


def configure_buffers(buffer_config: dict[str, dict]) -> tuple[dict[str, NumericEventBuffer], list[ReaderRouter]]:
    # ensure one router per reader, group buffers/routes by reader name
    pass


def configure_trials(trials_config: dict[str, Any]) -> tuple[TrialDelimiter, TrialExtractor]:
    pass


def configure_plotters(plotter_paths: list[str]) -> PlotFigureController:
    if not plotter_paths:
        logging.info(f"No plotters.")
        return PlotFigureController(plotters=[])

    logging.info(f"Using {len(plotter_paths)} plotters.")
    plotters = []
    for plotter_path in plotter_paths:
        logging.info(f"  {plotter_path}")
        plotters.append(Plotter.from_dynamic_import(plotter_path))

    return PlotFigureController(plotters)


# TODO: refactor this into the placeholder functions above
def configure_conversion(
    delimiter_csv: str,
    start_value: float,
    wrt_value: float,
    numeric_event_csvs: list[str],
    simulate_delay: bool = False
) -> tuple[TrialDelimiter, TrialExtractor, list[ReaderRouter]]:
    logging.info(f"Using delimiters from {delimiter_csv} start={start_value} wrt={wrt_value}")
    if simulate_delay:
        delimiter_reader = DelaySimulatorReader(CsvNumericEventReader(delimiter_csv, results_key="delimiters"))
    else:
        delimiter_reader = CsvNumericEventReader(delimiter_csv, results_key="delimiters")
    start_buffer = NumericEventBuffer()
    start_route = ReaderRoute("delimiters", "start")
    wrt_buffer = NumericEventBuffer()
    wrt_route = ReaderRoute("delimiters", "wrt")
    delimiter_router = ReaderRouter(
        delimiter_reader, {"start": start_buffer, "wrt": wrt_buffer},
        [start_route, wrt_route])
    delimiter = TrialDelimiter(start_buffer, start_value)

    routers = [delimiter_router]

    extra_buffers = {}
    if numeric_event_csvs:
        logging.info(f"Using {len(numeric_event_csvs)} extras:")
        for csv in numeric_event_csvs:
            name = Path(csv).stem
            logging.info(f"  {name}: {csv}")
            reader = CsvNumericEventReader(csv, results_key=name)
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
