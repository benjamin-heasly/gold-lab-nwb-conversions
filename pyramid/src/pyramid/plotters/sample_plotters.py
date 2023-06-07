import time
import numpy as np
from matplotlib.figure import Figure

from pyramid.gui import Plotter

class SampleSinePlotter(Plotter):

    def set_up(self, fig: Figure, experiment_info = {}, subject_info = {}) -> None:
        ax = fig.subplots()
        ax.set_ylim(-1.25, 1.25)
        self.x_values = np.linspace(0, 2*np.pi, 512)
        self.line = ax.plot(self.x_values, np.sin(self.x_values))
        self.start_time = time.time()

    def update(self, fig, current_trial, trials_info, experiment_info = {}, subject_info = {}) -> None:
        elapsed = time.time() - self.start_time
        self.line.set_ydata(np.sin(self.x_values + elapsed))


class SampleCosinePlotter(Plotter):

    def set_up(self, fig: Figure, experiment_info = {}, subject_info = {}) -> None:
        ax = fig.subplots()
        ax.set_ylim(-1.25, 1.25)
        self.x_values = np.linspace(0, 2*np.pi, 512)
        self.line = ax.plot(self.x_values, np.sin(self.x_values))
        self.start_time = time.time()

    def update(self, fig, current_trial, trials_info, experiment_info = {}, subject_info = {}) -> None:
        elapsed = time.time() - self.start_time
        self.line.set_ydata(np.sin(self.x_values + elapsed))
