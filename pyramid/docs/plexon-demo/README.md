# Signals Demo

Here's a demo / example of Pyramid with a Plexon .plx file.

TODO: revalidate since reader config changes

## overview

This example will read from a Plexon .plx file on your machine.
Since .plx files can be large, you'll have to bring your own.
Note the path of the file you want to use, for example,

```
/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Raw/MM_2022_08_05_REC.plx
```

Pyramid will read several event, spike event, and analog signal channels from the file.
By default it will read all of them, though this can be configured in the [demo_experiment.yaml](demo_experiment.yaml) (TODO).
It will delimit trials based on the "Strobed" event channel, using value 1005 to delimit trials and 1010 as the trial wrt event.
These are also configurable in the YAML.


## visualizing experiment configuration

Let's start by running Pyramid to generate an overview.

```
cd gold-lab-nwb-conversions/pyramid/docs/plexon-demo

pyramid graph --experiment demo_experiment.yaml --graph-file demo_experiment.png --readers plexon_reader.plx_file=/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Raw/MM_2022_08_05_REC.plx
```

This will produce a graph of Pyramid data sources and other configuration.

`demo_experiment.png`
![Graph of Pyramid Readers, Buffers, and Trial configuration for a Plexon file.](demo_experiment.png "Overview of a Plexon experiment")

This reflects much of the config set up in [demo_experiment.yaml](demo_experiment.yaml), which is the source of truth for this demo.

## running with plotters

We can run this demo experiment in `gui` mode to view the trials, events, and signals from the Plexon file.

```
cd gold-lab-nwb-conversions/pyramid/docs/plexon-demo

pyramid gui --experiment demo_experiment.yaml --trial-file demo_experiment.json --readers plexon_reader.plx_file=/home/ninjaben/Desktop/codin/gold-lab/plexon_data/MrM/Raw/MM_2022_08_05_REC.plx
```

This will open up a few figure windows.  You might want to arrange them.
One figure will contain basic info about the experiment, demo subject, and trial extraction progress.
The other figures will show trial-by-trial event and signal data.

The trials will update every few seconds, as if replaying the original acquisition timeline (in `gui` mode Pyramid can simulate delay while reading from data files.)

# WIP for reference...
dict_keys(['sig001_spikes', 'sig002_spikes', 'sig003_spikes', 'sig004_spikes', 'sig005_spikes', 'sig006_spikes', 'sig007_spikes', 'sig008_spikes', 'sig009_spikes', 'sig010_spikes', 'sig011_spikes', 'sig012_spikes', 'sig013_spikes', 'sig014_spikes', 'sig015_spikes', 'sig016_spikes', 'Event001', 'Event002', 'Event003', 'Event004', 'Event005', 'Event006', 'Event007', 'Event008', 'Event009', 'Event010', 'Event011', 'Event012', 'Event013', 'Event014', 'Event015', 'Event016', 'Strobed', 'Start18', 'Stop019', 'Keyboard1', 'Keyboard2', 'Keyboard3', 'Keyboard4', 'Keyboard5', 'Keyboard6', 'Keyboard7', 'Keyboard8', 'Keyboard9', 'AD01', 'AD02', 'AD03', 'AD04', 'AD05', 'AD06', 'AD07', 'AD08', 'AD09', 'AD10', 'AD11', 'AD12', 'AD13', 'AD14', 'AD15', 'AD16', 'AD17', 'AD18', 'AD19', 'AD20', 'AD21', 'AD22', 'AD23', 'AD24', 'AD25', 'AD26', 'AD27', 'AD28', 'AD29', 'AD30', 'AD31', 'AD32', 'AD33', 'AD34', 'AD35', 'AD36', 'AD37', 'AD38', 'AD39', 'AD40', 'AD41', 'AD42', 'AD43', 'AD44', 'AD45', 'AD46', 'AD47', 'AD48', 'Pupil', 'X50', 'Y51', 'AD52', 'AD53', 'AD54', 'AD55', 'AD56', 'AD57', 'AD58', 'AD59', 'AD60', 'AD61', 'AD62', 'AD63', 'AD64'])