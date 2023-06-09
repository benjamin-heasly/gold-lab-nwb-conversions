from typing import Any, Self
from pathlib import Path
import logging
from contextlib import ExitStack
from dataclasses import dataclass
import yaml
import graphviz

from pyramid.model.model import Buffer
from pyramid.neutral_zone.readers.readers import Reader, ReaderRoute, ReaderRouter, Transformer
from pyramid.neutral_zone.readers.delay_simulator import DelaySimulatorReader
from pyramid.trials.trials import TrialDelimiter, TrialExtractor, TrialEnhancer
from pyramid.trials.trial_file import TrialFileWriter
from pyramid.plotters.plotters import Plotter, PlotFigureController


@dataclass
class PyramidContext():
    subject: dict[str, Any]
    experiment: dict[str, Any]
    readers: dict[str, Reader]
    named_buffers: dict[str, Buffer]
    start_router: ReaderRouter
    other_routers: list[ReaderRouter]
    trial_delimiter: TrialDelimiter
    trial_extractor: TrialExtractor
    plot_figure_controller: PlotFigureController

    @classmethod
    def from_yaml_and_reader_overrides(
        cls,
        experiment_yaml: str,
        subject_yaml: str = None,
        reader_overrides: list[str] = [],
        allow_simulate_delay: bool = False
    ) -> Self:
        with open(experiment_yaml) as f:
            experiment_config = yaml.safe_load(f)

        # start_reader.csv_file=real.csv
        if reader_overrides:
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
            subject_config = {}

        pyramid_context = cls.from_dict(experiment_config, subject_config, allow_simulate_delay)
        return pyramid_context

    @classmethod
    def from_dict(
        cls,
        experiment_config: dict[str, Any],
        subject_config: dict[str, Any],
        allow_simulate_delay: bool = False
    ) -> Self:
        (readers, named_buffers, reader_routers) = configure_readers(experiment_config["readers"], allow_simulate_delay)
        (trial_delimiter, trial_extractor, start_buffer_name) = configure_trials(
            experiment_config["trials"], named_buffers)

        # Rummage around in the configured reader routers for the one associated with the trial "start" delimiter.
        start_router = None
        for router in reader_routers:
            for buffer_name in router.buffers.keys():
                if buffer_name == start_buffer_name:
                    start_router = router
        other_routers = [router for router in reader_routers if router != start_router]

        plotters = configure_plotters(experiment_config.get("plotters", []))
        subject = subject_config.get("subject", {})
        experiment = experiment_config.get("experiment", {})
        plot_figure_controller = PlotFigureController(
            plotters=plotters,
            experiment_info=experiment,
            subject_info=subject,
        )
        return PyramidContext(
            subject=subject,
            experiment=experiment,
            readers=readers,
            named_buffers=named_buffers,
            start_router=start_router,
            other_routers=other_routers,
            trial_delimiter=trial_delimiter,
            trial_extractor=trial_extractor,
            plot_figure_controller=plot_figure_controller
        )

    def run_without_plots(self, trial_file: str) -> None:
        """Run without plots as fast as the data allow.

        Similar to run_with_plots(), below.
        It seemed nicer to have separate code paths, as opposed to lots of conditionals in one uber-function.
        run_without_plots() should run without touching any GUI code, avoiding potential host graphics config issues.
        """
        with ExitStack() as stack:
            # All these "context managers" will clean up automatically when the "with" exits.
            writer = stack.enter_context(TrialFileWriter(trial_file))
            for reader in self.readers.values():
                stack.enter_context(reader)

            # Extract trials indefinitely, as they come.
            while self.start_router.still_going():
                got_start_data = self.start_router.route_next()
                if got_start_data:
                    new_trials = self.trial_delimiter.next()
                    for new_trial in new_trials:
                        for router in self.other_routers:
                            router.route_until(new_trial.end_time)
                            self.trial_extractor.populate_trial(
                                new_trial,
                                self.trial_delimiter.trial_count,
                                self.experiment,
                                self.subject
                            )
                        writer.append_trial(new_trial)
                        self.trial_delimiter.discard_before(new_trial.start_time)
                        self.trial_extractor.discard_before(new_trial.start_time)

            # Make a best effort to catch the last trial -- which would have no "next trial" to delimit it.
            self.start_router.route_next()
            for router in self.other_routers:
                router.route_next()
            last_trial = self.trial_delimiter.last()
            if last_trial:
                self.trial_extractor.populate_trial(
                    last_trial,
                    self.trial_delimiter.trial_count,
                    self.experiment,
                    self.subject
                )
                writer.append_trial(last_trial)

    def run_with_plots(self, trial_file: str) -> None:
        """Run with plots and interactive GUI updates.

        Similar to run_without_plots(), above.
        It seemed nicer to have separate code paths, as opposed to lots of conditionals in one uber-function.
        run_without_plots() should run without touching any GUI code, avoiding potential host graphics config issues.
        """
        with ExitStack() as stack:
            # All these "context managers" will clean up automatically when the "with" exits.
            writer = stack.enter_context(TrialFileWriter(trial_file))
            for reader in self.readers.values():
                stack.enter_context(reader)
            stack.enter_context(self.plot_figure_controller)

            # Extract trials indefinitely, as they come.
            while self.start_router.still_going() and self.plot_figure_controller.get_open_figures():
                self.plot_figure_controller.update()
                got_start_data = self.start_router.route_next()
                if got_start_data:
                    new_trials = self.trial_delimiter.next()
                    for new_trial in new_trials:
                        for router in self.other_routers:
                            router.route_until(new_trial.end_time)
                            self.trial_extractor.populate_trial(
                                new_trial,
                                self.trial_delimiter.trial_count,
                                self.experiment,
                                self.subject
                            )
                        writer.append_trial(new_trial)
                        self.plot_figure_controller.plot_next(new_trial, self.trial_delimiter.trial_count)
                        self.trial_delimiter.discard_before(new_trial.start_time)
                        self.trial_extractor.discard_before(new_trial.start_time)

            # Make a best effort to catch the last trial -- which would have no "next trial" to delimit it.
            self.start_router.route_next()
            for router in self.other_routers:
                router.route_next()
            last_trial = self.trial_delimiter.last()
            if last_trial:
                self.trial_extractor.populate_trial(
                    last_trial,
                    self.trial_delimiter.trial_count,
                    self.experiment,
                    self.subject
                )
                writer.append_trial(last_trial)
                self.plot_figure_controller.plot_next(last_trial, self.trial_delimiter.trial_count)

    def to_graphviz(self, graph_name: str, out_file: str):
        dot = graphviz.Digraph(
            name=graph_name,
            graph_attr={
                "rankdir": "LR",
                "label": graph_name
            }
        )

        all_routers = self.other_routers.copy()
        all_routers.append(self.start_router)
        named_routers = {}

        for name, reader in self.readers.items():
            label = f"{name}|{reader.__class__.__name__}"
            dot.node(name=name, label=label, shape="record")
            for router in all_routers:
                if router.reader is reader:
                    named_routers[name] = router

        start_buffer_name = None
        wrt_buffer_name = None
        for name, buffer in self.named_buffers.items():
            label = f"{name}|{buffer.__class__.__name__}|{buffer.data.__class__.__name__}"
            dot.node(name=name, label=label, shape="record")
            if buffer is self.trial_delimiter.start_buffer:
                start_buffer_name = name
            if buffer is self.trial_extractor.wrt_buffer:
                wrt_buffer_name = name

        for reader_name, router in named_routers.items():
            for index, route in enumerate(router.routes):
                route_name = f"{reader_name}_route_{index}"
                if route.transformers:
                    labels = [transformer.__class__.__name__ for transformer in route.transformers]
                    route_label = "|".join(labels)
                else:
                    route_label = "as is"
                dot.node(name=route_name, label=route_label, shape="record")

                dot.edge(reader_name, route_name, label=route.results_key)
                dot.edge(route_name, route.buffer_name)

        dot.node(
            name="trial_delimiter",
            label=f"{self.trial_delimiter.__class__.__name__}|start = {self.trial_delimiter.start_value}",
            shape="record"
        )
        dot.edge(
            start_buffer_name,
            "trial_delimiter",
            label="start",
            arrowhead="none",
            arrowtail="none")

        extractor_label = f"{self.trial_extractor.__class__.__name__}|wrt = {self.trial_extractor.wrt_value}"
        if self.trial_extractor.enhancers:
            enhancer_names = [enhancer.__class__.__name__ for enhancer in self.trial_extractor.enhancers]
            enhancers_label = "|".join(enhancer_names)
            extractor_label = f"{extractor_label}|{enhancers_label}"
        dot.node(
            name="trial_extractor",
            label=extractor_label,
            shape="record"
        )
        dot.edge(
            wrt_buffer_name,
            "trial_extractor",
            label=f"wrt",
            arrowhead="none",
            arrowtail="none"
        )

        out_path = Path(out_file)
        file_name = f"{out_path.stem}.dot"
        dot.render(directory=out_path.parent, filename=file_name, outfile=out_path)


def configure_readers(
    readers_config: dict[str, dict],
    allow_simulate_delay: bool = False
) -> tuple[dict[str, Reader], dict[str, Buffer], list[ReaderRouter]]:
    readers = {}
    named_buffers = {}
    routers = []
    for (reader_name, reader_config) in readers_config.items():
        # Instantiate the reader by dynamic import.
        reader_class = reader_config["class"]
        reader_args = reader_config.get("args", {})
        simulate_delay = allow_simulate_delay and reader_config.get("simulate_delay", False)
        reader = Reader.from_dynamic_import(reader_class, **reader_args)
        if simulate_delay:
            reader = DelaySimulatorReader(reader)
        readers[reader_name] = reader

        # Instantiate routes and their buffers for this reader.
        reader_routes = []
        buffers_config = reader_config.get("buffers", {})
        for buffer_name, buffer_config in buffers_config.items():

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
        reader_router = ReaderRouter(reader, reader_routes)
        routers.append(reader_router)
        named_buffers.update(reader_router.buffers)

    return (readers, named_buffers, routers)


def configure_trials(
    trials_config: dict[str, Any],
    named_buffers: dict[str, Buffer]
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

    other_buffers = {name: buffer for name, buffer in named_buffers.items()
                     if name != start_buffer_name and name != wrt_buffer_name}

    enhancers = []
    enhancers_config = trials_config.get("enhancers", [])
    for enhancer_config in enhancers_config:
        enhancer_class = enhancer_config["class"]
        enhancer_args = enhancer_config.get("args", {})
        enhancer = TrialEnhancer.from_dynamic_import(enhancer_class, **enhancer_args)
        enhancers.append(enhancer)

    trial_extractor = TrialExtractor(
        wrt_buffer=named_buffers[wrt_buffer_name],
        wrt_value=wrt_value,
        wrt_value_index=wrt_value_index,
        named_buffers=other_buffers,
        enhancers=enhancers
    )

    return (trial_delimiter, trial_extractor, start_buffer_name)


def configure_plotters(plotters_config: list[dict[str, str]]) -> list[Plotter]:
    if not plotters_config:
        logging.info(f"No plotters.")
        return []

    logging.info(f"Using {len(plotters_config)} plotters.")
    plotters = []
    for plotter_config in plotters_config:
        plotter_class = plotter_config["class"]
        plotter_args = plotter_config.get("args", {})
        logging.info(f"  {plotter_class}")
        plotters.append(Plotter.from_dynamic_import(plotter_class, **plotter_args))

    return plotters
