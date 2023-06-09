# Signals Demo

Here's a demo / example of Pyramid signal chunks and plotting.

## overview

This example will read from two CSV files.
The first, [delimiter.csv](delimiter.csv), will partition about a minute of time into 10 trials.
The second, [demo_signal.csv](demo_signal.csv) contains many samples of the sine and cosine functions, over time.

Pyramid will read in the delimiter events and signal data, partition them into trials, and plot signal chunks for each trial.  The signal chinks will stack up near each other, from trial to trial.

## visualizing experiment configuration

Let's start by running Pyramid to generate an overview of a demo experiment.

```
cd gold-lab-nwb-conversions/pyramid/docs/signal-demo

pyramid graph --experiment demo_experiment.yaml --graph-file demo_experiment.png
```

This will produce a graph of Pyramid data sources and other configuration.

`demo_experiment.png`
![Graph of Pyramid Readers, Buffers, and Trial configuration for demo_experiment.](demo_experiment.png "Overview of demo_experiment")

This reflects much of the config set up in [demo_experiment.yaml](demo_experiment.yaml), which is the source of truth for this demo.

## running with plotters

We can run this demo experiment in `gui` mode to view the signals.

```
cd gold-lab-nwb-conversions/pyramid/docs/signal-demo

pyramid gui --experiment demo_experiment.yaml --trial-file demo_trials.json --readers delimiter_reader.csv_file=delimiter.csv signal_reader.csv_file=demo_signal.csv
```

This will open up two figure windows.  You might want to arrange them.
One figure will contain basic info about the experiment, demo subject, and trial extraction progress.
The other figure will show signal chunks assigned to each trial.

`signal_plotter.png`
![Plot of signal chunks, overlayed trial after trial.](signal_plotter.png "Plot of signal chunks")


The trials will update about every 10 seconds (in `gui` mode Pyramid can simulate delay while reading from data files.)
