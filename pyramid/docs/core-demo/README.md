# Core Demo

Here's a demo / example of Pyramid's core functionality so far.

## overview

This example will read event data from several CSV files.
Some of the events will be used to delimit trials in time and to align data within a trial.
Other events will be selected based on delimited times, aligned, and assigned to appropriate trials.
Pyramid will write each trial to a JSON "trial file", as it goes along.

## visualizing experiment configuration

Let's start by running Pyramid to generate an overview of a demo experiment.
After that we'll go back and look at each part in more detail.

Try running the following:

```
cd gold-lab-nwb-conversions/pyramid/docs/core-demo

pyramid graph --graph-file demo_experiment.png --experiment demo_experiment.yaml --readers delimiter_reader.csv_file=delimiter.csv foo_reader.csv_file=foo.csv bar_reader.csv_file=bar.csv
```

This will produce a graph of Pyramid data sources and other configuration.
Having a graph is useful for this demo.
In general, graphs like this should give you a way to check whether Pyramid interpreted your experiment the way you expected.

`demo_experiment.png`
![Graph of Pyramid Readers, Buffers, and Trial configuration for demo_experiment.](demo_experiment.png "Overview of demo_experiment")

From this graph, we can see that Pyramid intends to:

 - read event data from 3 different CSV files
 - deal events as they arrive into 4 different named buffers
 - transform event values on the way into one of those buffers, but leave the other three "as is"
 - delimit trials based on events in buffer named "delimiter"
 - align data within each trial based on other events in the buffer named "delimiter"
 - add additional data to trials from buffers named "foo", "bar", and "bar_2"


## configuration with YAML

The [demo_experiment.yaml](demo_experiment.yaml) we graphed above is an example of a Pyramid experiment [YAML](https://en.wikipedia.org/wiki/YAML) file.
Each experiment design or rig setup would have its own YAML file to capture and declare how the experiment is set up, including things like:

 - basic descriptions of the experiment design and lab
 - which data sources to read into the Pyramid Neutral Zone
 - how to delimit and align trials based on the events as they arrive
 - how to interpret and transform raw data into meaningful concepts like:
   - the analog signal on a particular channel is "pupil diameter"
   - distict numeric events from a particular source should be grouped and converted into string-valued "matlab commands"

The main sections of each YAML file are:

 - `experiment` -- basic description of the experiment design and lab, suitable for including in an NWB file.
 - `readers` -- detailed description of data sources to read from, how to map and transform data from those sources into named buffers
 - `trials` -- how to delimit trials in time and align data within each trial based on events as they arrive
 - `plotters` -- optionally, how to visualize each trial as it arrives

## data sources

This demo experiment reads data from three CSV files.
CSV is a simple format, easy to get started with.
Going forward we expect to read data from other online and offline sources like Plexon, Open Ephys and NWB.

Since the CSVs in this demo are small, we can just look at them here and get a sense for what should happen when Pyramid runs.

### delimiter
[delimiter.csv](delimiter.csv) determines the structure of trials in time.

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

For the demo experiment Pyramid will treat events with value `1010` as trial starts and ends.
It will treat events with value `42` as trial "with respect to" events for aligning data to a zero-time within each trial.

Based on the `1010` delimiting events, we'd expect the following trials:
 - trial 0 -- everything preceeding the first "start" at time `1.0`
 - trial 1 -- a trial between "start" events at times `1.0` and `2.0`
 - trial 2 -- a trial between "start" events at times `2.0` and `3.0`
 - trial 3 -- a last trial, everything after the last "start" at time `3.0`

Based on the `42` wrt events, each trial other than trial 0 would have its data aligned to a "zero" time half way through the trial.

### foo
[foo.csv](foo.csv) is an example of additional data to be added to a trial after the trial has been delimited above.  These show how data are assigned to trials based on the trial's time range, and how they can be aligned in time with respect to the wrt event in each trial.

```
time,   value
0.2,    0
1.2,    0
1.3,    1
2.2,    0
2.3,    1
```

Foo has events that arrive during trials 0, 1, and 2, but not trial 3.  It will turn out that these events arrive before the wrt events in trials 1 and 2, so they will have negative time stamps in those trials. 

### bar
[bar.csv](bar.csv) is another example of data to be added to each trial after it's delimited.

```
time,   value
0.1,    1
3.1,    0
```

Bar has events that arrive during trials 0 and 3, but not 1 or 2.  It will turn out that the event in trial 3 arrives before the wrt event in that trial, so it will end up with a negative time stamp.

The demo experiment will use data it reads from `bar.csv` twice!  This will demonstrate flexibility in how data can be read in, then mapped and transformed before being put into trials.

 - direct use: copy events directly into a buffer named "bar".
 - transformed use: copy events, apply a gain and offset to the event values, and put in a separate buffer named "bar_2"

## running a conversion

So far, we've looked at input data and Pyramid experiment configuration.
Now let's put those together and let Pyramid run through the data and convert events to trials.

```
cd gold-lab-nwb-conversions/pyramid/docs/core-demo

pyramid convert --trial-file demo_trials.json --experiment demo_experiment.yaml --readers delimiter_reader.csv_file=delimiter.csv foo_reader.csv_file=foo.csv bar_reader.csv_file=bar.csv
```

As above, this invokes Pyramid on our experiment YAML file.
Instead of `graph` mode, it uses `convert` mode to actually run through the data.

In addition, it specifies several CSV filenames for each reader to use.
We could have put those file names directly into the `demo_experiment.yaml` file, and that would work fine.
But maybe the specifc files to use need to change each experiment session.  Instead of having to edit the YAML each time, we can override specific reader args from the command line.

Finally, it specifies `demo_trials.json` as the output trial file to write.

### trial file

Let's look at the trial file to see if it matches our expectations from above.
For this demo the trial file is not very long, and it looks like this (mildly formatted here for clarity):

```
{"start_time": 0.0, "end_time": 1.0, "wrt_time": 0.0, "numeric_events": {"foo": [[0.2, 0.0]], "bar": [[0.1, 1.0]], "bar_2": [[0.1, -22.0]]}},
{"start_time": 1.0, "end_time": 2.0, "wrt_time": 1.5, "numeric_events": {"foo": [[-0.3, 0.0], [-0.2, 1.0]], "bar": [], "bar_2": []}},
{"start_time": 2.0, "end_time": 3.0, "wrt_time": 2.5, "numeric_events": {"foo": [[-0.3, 0.0], [-0.2, 1.0]], "bar": [], "bar_2": []}},
{"start_time": 3.0, "end_time": null, "wrt_time": 3.5, "numeric_events": {"foo": [], "bar": [[-0.4, 0.0]], "bar_2": [[-0.4, -20.0]]}}
```

Each trial found during the `convert` run is written to its own line in the trial file.
As a whole, the file uses the [JSON Lines](https://jsonlines.org/) convention where each line of the file is a valid JSON object.

We got 4 trials as expected, delimited by start and end times that fall on whole-numbered seconds.
Each trial has a wrt time that falls between the start and end.
Data from the "foo", "bar", and "bar_2" buffers are assigned to each trial based on start and end times, and then aligned to the wrt time.

## running with plotters

Pyramid `convert` mode probably makes sense when running conversions offline, when we want things to run as fast as the data will allow.

Pyramid also has a `gui` mode which probaly makes sense when running online, during live acquisition.
In `gui` mode Pyramid can manage figure windows and update data plots after each trial.

```
cd gold-lab-nwb-conversions/pyramid/docs/core-demo

pyramid gui --trial-file demo_trials.json --experiment demo_experiment.yaml --readers delimiter_reader.csv_file=delimiter.csv foo_reader.csv_file=foo.csv bar_reader.csv_file=bar.csv
```

This command is identical to the `convert` command above, except for the mode argument, which is now `gui`.

A figure window should open and update every second as new trials arrive.
The plot in this example just shows basic trial extraction progress.
Custom plots can also be created, and configured in the `plotters` section of the experiment YAML.

### simulating delay

Why does `gui` mode run for several seconds, when the data are just sitting there in CSV files?
This is because Pyramid is simulating the delay between trial "start" event time stamps, as written `delimiter.csv`.
Delay simulation is optional for demo purposes and only happens if a reader's YAML contains `simulate_delay: True`.

## loading JSON trial file in Matlab

It should be possible to read a JSON trial file in a variety of environments, not just Pyramid or Python.
Here's a Matlab example for reading lines of JSON into from a trial file into a struct array.

```
trialFile = 'demo_trials.json';
trialCell = {};
fid = fopen(trialFile, 'r');
while true
    trialJson = fgetl(fid);
    if ~ischar(trialJson) || isempty(trialJson)
        break
    end
    trialCell{end+1} = jsondecode(trialJson);
end

trials = [trialCell{:}]
%  trials =
%
%    1×4 struct array with fields:
%
%      start_time
%      end_time
%      wrt_time
%      numeric_events

events = [trials.numeric_events]
%  events =
%
%    1×4 struct array with fields:
%
%      foo
%      bar
%      bar_2
```

This example loads all the lines/trials into memory at once.
For larger trial files it might be better to load one or a few trials at a time (i.e. don't always append loaded trials to one big array).

## HDF5 trial file

Pyramid can also produce trial files using HDF5.
This is a binary format that supports folder-like "Groups" and numeric array-like "Datasets".
It's likely to be faster and smaller than JSON, though potentially less portable and less human-readable for tutorial purposes.

To create an HDF5 trial file, just use the `.hdf5` extension for the '--trial-file' argument.
```
cd gold-lab-nwb-conversions/pyramid/docs/core-demo

pyramid convert --trial-file demo_trials.hdf5 --experiment demo_experiment.yaml --readers delimiter_reader.csv_file=delimiter.csv foo_reader.csv_file=foo.csv bar_reader.csv_file=bar.csv
```

Matlab supports reading HDF5 files.
Here's a Matlab example for reading trials from an HDF5 trial file into a struct array.
This takes a little more coding than for the JSON example above.
This is because there are many potentially reasonable ways to convet between Python data types, HDF5 data types, and Matlab data types, and the conventions are not as obvious or 1:1 as they are with JSON.

```
trialFile = 'demo_trials.hdf5';
info = h5info(trialFile);
trialCell = {};
for trialGroup = info.Groups'
    trial = struct();

    % Get top-level trial fields like start_time, end_time, and wrt_time.
    % Decode any trial enhancements from JSON.
    for attribute = trialGroup.Attributes'
        switch attribute.Name
            case 'enhancements'
                trial.enhancements = jsondecode(attribute.Value);
            otherwise
                trial.(attribute.Name) = attribute.Value;
        end
    end

    % Unpack data assigned to the trial, depending on Neutral Zone type.
    for dataGroup = trialGroup.Groups'
        subgroupName = dataGroup.Name(numel(trialGroup.Name)+2:end);
        switch subgroupName
            case 'numeric_events'
                for dataset = dataGroup.Datasets'
                    dataPath = [dataGroup.Name '/' dataset.Name];
                    data = h5read(trialFile, dataPath);
                    trial.numeric_events.(dataset.Name) = data';
                end

            case 'signals'
                for dataset = dataGroup.Datasets'
                    dataPath = [dataGroup.Name '/' dataset.Name];
                    data = h5read(trialFile, dataPath);
                    trial.signals.(dataset.Name).sample_data = data';

                    for attribute = dataset.Attributes'
                        trial.signals.(dataset.Name).(attribute.Name) = attribute.Value;
                    end
                end
        end
    end

    trialCell{end+1} = trial;
end

trials = [trialCell{:}]
trials =

  1×4 struct array with fields:

    start_time
    end_time
    wrt_time
    numeric_events

events = [trials.numeric_events]
events =

  1×4 struct array with fields:

    bar
    bar_2
    foo
```

Note: this still uses a little bit of JSON to encode/decode trial `enhamcements`, which are arbitrary key-value pairs and support nested collections like dictionaries and lists.  But the bulk of trial event and signal data are stored using HDF5's compressed, binary format.

As above, this example loads all the trials into memory at once.
HDF5 also supports reading files a piece at a time, even for very large files.
For larger trial files it might be better to load one or a few trials at a time (i.e. don't always append loaded trials to one big array).
