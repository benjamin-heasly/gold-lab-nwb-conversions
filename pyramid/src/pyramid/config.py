from typing import Any, Self
import logging
from dataclasses import dataclass
import yaml

from pyramid.neutral_zone.readers.readers import Reader, ReaderRoute, ReaderRouter, Transformer
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
    start_router: ReaderRouter
    other_routers: list[ReaderRouter]
    trial_delimiter: TrialDelimiter
    trial_extractor: TrialExtractor
    plot_figure_controller: PlotFigureController

    def to_graphviz(self):
        pass

    @classmethod
    def from_yaml_and_reader_overrides(cls, experiment_yaml: str, subject_yaml: str = None, reader_overrides: list[str] = []) -> Self:
        with open(experiment_yaml) as f:
            experiment_config = yaml.safe_load(f)

        # start_reader.csv_file=real.csv
        for override in reader_overrides:
            (reader_name, assignment) = override.split(".", maxsplit=1)
            (property, value) = assignment.split("=", maxsplit=1)
            reader_config = experiment_config["readers"][reader_name]
            reader_args = reader_config.get("args", {})
            reader_args[property] = value
            reader_config["args"] = reader_args

        if subject_yaml:
            with open(subject_yaml) as f:
                subject_config = yaml.safe_load(f)
        else:
            subject_config = None

        pyramid_config = PyramidConfig.from_dict(experiment_config, subject_config)
        return pyramid_config

    @classmethod
    def from_dict(cls, experiment_config: dict[str, Any], subject_config: dict[str, Any]) -> Self:
        (readers, named_buffers, reader_routers) = configure_readers(experiment_config["readers"])
        (trial_delimiter, trial_extractor, start_buffer_name) = configure_trials(experiment_config["trials"], named_buffers)

        # Rummage around in the configured reader routers for the one associated with the trial "start" delimiter.
        start_router = None
        for router in reader_routers:
            for buffer_name in router.buffers.keys():
                if buffer_name == start_buffer_name:
                    start_router = router
        other_routers = [router for router in reader_routers if router != start_router]

        plot_figure_controller = configure_plotters(experiment_config.get("plotters", []))
        return PyramidConfig(
            subject=subject_config,
            experiment=experiment_config.get("experiment", {}),
            readers=readers,
            named_buffers=named_buffers,
            start_router=start_router,
            other_routers=other_routers,
            trial_delimiter=trial_delimiter,
            trial_extractor=trial_extractor,
            plot_figure_controller=plot_figure_controller
        )


def configure_readers(
    readers_config: dict[str, dict]
) -> tuple[dict[str, Reader], dict[str, NumericEventBuffer], list[ReaderRouter]]:
    readers = {}
    named_buffers = {}
    routers = []
    for (reader_name, reader_config) in readers_config.items():
        # Instantiate the reader by dynamic import.
        reader_class = reader_config["class"]
        reader_args = reader_config.get("args", {})
        simulate_delay = reader_config.get("simulate_delay", False)
        reader = Reader.from_dynamic_import(reader_class, **reader_args)
        if simulate_delay:
            reader = DelaySimulatorReader(reader)
        readers[reader_name] = reader

        # Instantiate buffers and routes for this reader.
        reader_buffers = {}
        reader_routes = []
        buffers_config = reader_config.get("buffers", {})
        for buffer_name, buffer_config in buffers_config.items():
            reader_buffers[buffer_name] = NumericEventBuffer()

            # Instantiate transformers by dynamic import.
            transformers = []
            transformers_config = buffer_config.get("transformers", [])
            for transformer_config in transformers_config:
                transformer_class = transformer_config["class"]
                transformer_args = transformer_config.get("args", {})
                transformer = Transformer.from_dynamic_import(transformer_class, **transformer_args)
                transformers.append(transformer)

            results_key = buffer_config.get("results_key", [])
            route = ReaderRoute(results_key, buffer_name, transformers)
            reader_routes.append(route)

        # A router to route data from the reader along each configured route to its buffer.
        reader_router = ReaderRouter(reader, reader_buffers, reader_routes)
        routers.append(reader_router)
        named_buffers.update(reader_buffers)

    return (readers, named_buffers, routers)


def configure_trials(
    trials_config: dict[str, Any],
    named_buffers: dict[str, NumericEventBuffer]
) -> tuple[TrialDelimiter, TrialExtractor, str]:
    start_buffer_name = trials_config.get("start_buffer", "start")
    start_value = trials_config.get("start_value", 0.0)
    start_value_index = trials_config.get("start_value_index", 0)
    trial_start_time = trials_config.get("trial_start_time", 0.0)
    trial_count = trials_config.get("trial_count", 0)
    trial_delimiter = TrialDelimiter(
        start_buffer=named_buffers[start_buffer_name],
        start_value=start_value,
        start_value_index=start_value_index,
        trial_start_time=trial_start_time,
        trial_count=trial_count
    )

    wrt_buffer_name = trials_config.get("wrt_buffer", "wrt")
    wrt_value = trials_config.get("wrt_value", 0.0)
    wrt_value_index = trials_config.get("wrt_value_index", 0)

    other_buffers = {name: buffer for name, buffer in named_buffers.items() if name != start_buffer_name and name != wrt_buffer_name}
    trial_extractor = TrialExtractor(
        wrt_buffer=named_buffers[wrt_buffer_name],
        wrt_value=wrt_value,
        wrt_value_index=wrt_value_index,
        named_buffers=other_buffers
    )

    return (trial_delimiter, trial_extractor, start_buffer_name)


def configure_plotters(plotters_config: list[dict[str, str]]) -> PlotFigureController:
    if not plotters_config:
        logging.info(f"No plotters.")
        return PlotFigureController(plotters=[])

    logging.info(f"Using {len(plotters_config)} plotters.")
    plotters = []
    for plotter_config in plotters_config:
        plotter_class = plotter_config["class"]
        plotter_args = plotter_config.get("args", {})
        logging.info(f"  {plotter_class}")
        plotters.append(Plotter.from_dynamic_import(plotter_class, **plotter_args))

    return PlotFigureController(plotters)
