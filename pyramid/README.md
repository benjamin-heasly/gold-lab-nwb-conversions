# Pyramid

This folder contains a Python project called Pyramid.
"Pyramid" is a pun on "Python" and "FIRA", the Gold Lab's existing analysis tools.
Pyramid is intended as a successor to FIRA.

Pyramid reads data from various sources into a simple, shared data model called the "Neutral Zone".
Based on event times in the Neutral Zone, it delimits trials in time.
It populates each trial with data from various sources, configured by a YAML file.
It produces a JSON "trial file" with one big array of trials.

Pyramid can run "online" as an experiment happens or "offline" for later data combining and analysis.
Either way, it views data in a streaming way, as a sliding window over time.
This approach is helpful for dealing with live data, as well as large data files.

![Pyramid reads data into the Neutral Zone and delimits and extracts Trials.](docs/pyramid-sketch-Page-1.png "Pyramid overview")

# Demo / Example

Pyramid is a work in progress.
Here's a demo / example of the core functionality.

## overview

This example will read event data from several CSV files.
Some of the events will be used to delimit trials in time and align times within a trial.
Other events will just be added to populate trial.
Pyramid will write each trial to a JSON "trial file", as it goes along.

The files used in this demo are located here in this repo at [core-demo](docs/core-demo).

## jump ahead: visualizing configuration

Let's start the demo by running Pyramid to generate an overview of the example experiment.
Then we'll go back and look at each part in more detail.

If you haven't already, you'll need to [install Pyramid](#Installation).
Then you can generate the overview:

```
cd gold-lab-nwb-conversions/pyramid/docs/core-demo
pyramid graph --experiment demo_experiment.yaml
```

For this demo, the graph us something nice to look at.
In general, graphs like this should give you a way to check whether Pyramid interpreted your experiment the way you expected.

![Graph of Pyramid Readers, Buffers, and Trial configuration for demo_experiment.](docs/demo_experiment.png "Overview of demo_experiment")

To summarize this demo experiment, Pyramid will:

 - read event data from 3 different CSV files
 - deal events as they arrive into 5 different named buffers
 - transform event values on the way into one of those buffers
 - delimit trials based on events in buffer named "start"
 - align data in time within each trial, based on events in another buffer named "wrt"
 - add aligned data from the other buffers to each trial


## configuration with YAML

The [demo_experiment.yaml](docs/core-demo/demo_experiment.yaml) we graphed above is an example of a Pyramid experiment [YAML](https://en.wikipedia.org/wiki/YAML) file.
Each experiment design or rig setup would have its own YAML file to capture and declare how the experiment is set up, including things like:

 - basic descriptoins of the experiment, lab, and subject
 - which data sources to read into the Pyramid Neutral Zone
 - how to delimit and align trials based on the events as they arrive
 - how to interpret and transform raw data into meaningful concepts like:
   - the analog signal on a particular channel is "pupil diameter"
   - distict numeric events from a particular source should be grouped and converted into string-valued "matlab commands"

The main sections of each YAML file are:

 - `experiment` -- basic description of the experiment design and lab, suitable for including in an NWB file.
 - `readers` -- detail description of data sources to read from, how to arrange data from those sources into named buffers, and optionally how to transform the data on the way from reader to buffer
 - `trials` -- how to delimit trials in time and align data within each trial, based on events as they arrive
 - `plotters` -- optionally, how to visualize each trial as it arrives

## data sources

This demo experiment reads data from three CSV files.
CSV is a simple format, easy to get started with.
We'd expect to read data from other live and file source as well including Plexon, Open Ephys, NWB, and more.

Since the CSVs in this demo are small, we can just look at them and descrive how we expect Pyramid to use them.

### delimiter
[delimiter.csv](docs/core-demo/delimiter.csv) determines the structure of trials in time.

```
time,   value
1.0,    1010
1.5,    42
2.0,    1010
2.5,    42
2.6,    42
3.0,    1010
3.5,    42
```

Each row is interpreted as one event.  The first column has the event time stamp, the second column has a numeric event value.
The first header row is ignored.
The demo experiment tells Pyramid to treat events with value `1010` as delimiting trial starts and ends/
It tells Pyramid to treat events with value `42` as trial "with respect to" events that determine the "zero" time within each trial.

Based on the `1010` delimiting events, we'd expect the following trials:
 - trial 0 -- everything preceeding the first "start" at time `1.0`
 - trial 1 -- a trial between "start" events at times `1.0` and `2.0`
 - trial 2 -- a trial between "start" events at times `2.0` and `3.0`
 - trial 3 -- a last trial, everything after the last "start" at time `3.0`

Based on the `42` wrt events, each trial other than trial 0 would have its data aligned to a "zero" time half way through the trial.

### foo
[foo.csv](docs/core-demo/foo.csv)is an example of other data that gets added to a trial after the trial has been delimited as above.  These events are not especially meaningful, but they do show how data are assigned to trials based on the trial's time range, and how they can be "zero" aligned based on the wrt event in each trial.

```
time,   value
0.2,    0
1.2,    0
1.3,    1
2.2,    0
2.3,    1
```

Foo has events that arrive during trials 0, 1, and 2.  It will turn out that these events arrive before the wrt events in trials 1 and 2, which means within those trials, the events will have negative time stamps.

### bar
[bar.csv](docs/core-demo/bar.csv) is another example of data added to a trial after the trial has been delimited.

```
time,   value
0.1,    1
3.1,    0
```

Bar has events that arrive during trials 0 and 3.  It will turn out that the event in trial 3 arrives before the wrt events in that trial, so it will also end up with a negative time stamp.

The demo experiment uses the bar data twice:

 - direct use: copy events directly into a buffer named "bar".
 - transformed use: copy events, apply a gain and offset to the event values, and put in a separate buffer named "bar_2"

This demonstrates flexibility in how data are read in, then mapped and transformed, before being put into trials. 

## running a conversion

So far, we've looked at input data and Pyramid experiment configuration.
Now let's put those together and run Pyramid to read in all the data and convert to trials.

```
cd gold-lab-nwb-conversions/pyramid/docs/core-demo
pyramid convert --experiment demo_experiment.yaml --readers delimiter_reader.csv_file=delimiter.csv foo_reader.csv_file=foo.csv bar_reader.csv_file=bar.csv --trial-file demo_trials.json
```

As above, this invokes Pyramid on our experiment YAML file.
Instead of `graph` mode, it uses `convert` mode to actually run through the data.

In addition, it specifies specific CSV filenames to use for each reader.
We could have put those file names directly into the `demo_experiment.yaml` file, and that would work fine.
The idea here is that we might have multiple data files belonging to the same experiment, for example from different sessions.
Instead of having to edit the YAML for each session, we can override specific reader args from the command line.

Finally, it specifies `demo_trials.json` as the output file where trials should be written.

### trial file

Let's look at the trial file to see if it matches our expectations from above.
For this demo the trial file is not very long, and it looks like this:

```
[
{"start_time": 0.0, "end_time": 1.0, "wrt_time": 0.0, "numeric_events": {"foo": [[0.2, 0.0]], "bar": [[0.1, 1.0]]}},
{"start_time": 1.0, "end_time": 2.0, "wrt_time": 1.5, "numeric_events": {"foo": [[-0.30000000000000004, 0.0], [-0.19999999999999996, 1.0]], "bar": []}},
{"start_time": 2.0, "end_time": 3.0, "wrt_time": 2.5, "numeric_events": {"foo": [[-0.2999999999999998, 0.0], [-0.20000000000000018, 1.0]], "bar": []}},
{"start_time": 3.0, "end_time": null, "wrt_time": 3.5, "numeric_events": {"foo": [], "bar": [[-0.3999999999999999, 0.0]]}}
]
```

Each trial found during the `convert` run is written to its own line in the trial file.
In addition, the whole trial file is a valid JSON array of trial objects.

We got 4 trials as expected, delimited by start and end times that fall on whole-numbered seconds.
Each trial has a "wrt" time between the start and end end, used to "zero" align data within each trial.
Each trial has events assigned to it from the "foo" and "bar" data sources, including "bar_2" which is a transformed version of the raw "bar" data.
Within each trial the assigned data have the "wrt" time subtracted out, causing some events to end up with negative time stamps, with respect to the trial.

## running with plotters

Pyramid `convert` mode probably makes sense when running conversions offline, when we want things to run as fast as the data will allow.

Pyramid also has a `gui` mode which probaly makes sense when running online, on live data.
In `gui` mode Pyramid can manage figure windows and update data plots after each trial.

```
cd gold-lab-nwb-conversions/pyramid/docs/core-demo
pyramid gui --experiment demo_experiment.yaml --readers delimiter_reader.csv_file=delimiter.csv foo_reader.csv_file=foo.csv bar_reader.csv_file=bar.csv --trial-file demo_trials.json
```

This command is identical to the `convert` command above, except for the mode argument, which is now `gui`.
A figure window should open and update every few seconds as new trials arrive.
The plot in this example just shows basic trial extraction progress.
Custom plots can also be created, and configured in the `plotters` section of the experiment YAML.

### simulating delay

Why does `gui` mode run for several seconds, when the data are just sitting there in CSV files?
This is because Pyramid is simulating the delay between trial "start" event time stamps, as written `delimiter.csv`.
Delay simulation is optional and only happens if a reader's YAML contains `simulate_delay: True`.

## loading data in Matlab

Since the trial file is JSON, trial data should be readable in a variety of environments, not just Pyramid or Python.
Here's an example reading a trial file into Matlab.

```
trial_file = 'trials.json';
trial_json = fileread(trial_file, "Encoding", "UTF-8");
trials = jsondecode(trial_json)

trials = 

  4×1 struct array with fields:

    start_time
    end_time
    wrt_time
    numeric_events
```

For trial files small enough to load in to memory, this might be all you need!
For larger trial files, we might need custom Matlab code that read part of the data at a time.

# Installation

You should be able to install Pyramid on any machine -- you don't need a special machine like the lab's Neuropixels machine.

## conda
We've been using the `conda` tool to set up Python environments with the desired versions of Python and dependencies.
Here are instructions for [installing miniconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)

With that you can obtain this repo and set up our `gold_nwb` conda environment.

```
git clone https://github.com/benjamin-heasly/gold-lab-nwb-conversions
cd gold-lab-nwb-conversions
conda env create -f environment.yml
```

If you've already dont this in the past but you want to make sure you're up to date, you can update the environment.

```
cd gold-lab-nwb-conversions
git pull
conda env update -f environment.yml --prune
```

## pyramid

No you can install Pyramid from this repo into the `gold_nwb` environment on your machine.

```
conda activate gold_nwb
cd pyramid
pip install .
pyramid --help
```

## dev tools

During development I'm also using [hatch](https://github.com/pypa/hatch) and [pytest](https://docs.pytest.org/en/7.1.x/getting-started.html)  to manage Pyramid as a Python project.  Most users won't need to use these.

I'm manually installing these into the `gold_nwb` environment on my machine.

```
conda activate gold_nwb
pipx install hatch
pip install pytest
```

I'm running the Pyramid unit and integration tests like this:

```
cd pyramid
hatch run test:cov
```

Hatch is smart enough to install pytest automatically in the tests environment it creates.
The reason I also install pytest manually is so that my IDE recognizes pytest for syntax highlighting, etc.
