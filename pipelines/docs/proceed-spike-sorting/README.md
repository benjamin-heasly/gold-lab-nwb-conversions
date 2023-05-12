# March-May 2023
Ben Heasly

[benjamin.heasly@gmail.com](mailto:benjamin.heasly@gmail.com)

[https://www.tripledip.info/](https://www.tripledip.info/)


Here's an overview of our new sorting pipeline for Plexon with Kilosort!

This one uses our [Proceed](https://github.com/benjamin-heasly/proceed) tool to run pipelines declared in YAML files.

Hopefully this is preferable to cutting and pasting commands into the terminal, as in our [manual proof of concept pipeline](../manual-poc/README.md).

This document started as a Google Doc [here](https://docs.google.com/document/d/1XrfAMFngeLdG7fOxbnDsMQYHO39rXbhZy_HKfMlxpOw/edit?usp=sharing).
You may or may not have access to that doc.
I [converted it to Markdown](https://workspace.google.com/marketplace/app/docs_to_markdown/700168918607) so we could save it here in [this repo](https://github.com/benjamin-heasly/gold-lab-nwb-conversions).


# Installation

The Proceed repo is at GitHub here: [proceed](https://github.com/benjamin-heasly/proceed)

And the main docs, including installation instructions are here: [proceed docs](https://benjamin-heasly.github.io/proceed/index.html)


## Neuropixels Machine

[Docker](https://docs.docker.com/desktop/install/windows-install/) and Python are already installed on the Gold Lab Neuropixels machine.

[Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html) is also installed, to manage Python environments.

Proceed itself is still evolving pretty quickly, so it makes sense to update it before you use it.

First get into WSL, which is our Ubuntu Linux environment within Windows.  Open the Windows Command Prompt and type `wsl` to enter Linux mode.

![windows command prompt](images/windows-command-prompt.png)

```
wsl
```


Run the following to get and install the latest version of Proceed.


```
# Activate our Python environment
conda activate pipeline-stuff

# Get the latest code
cd /mnt/d/repos/proceed
git pull

# Install Proceed from source code, in our Conda environment.
pip install .
```



# Spike Sorting with Kilosort and Phy

Here are some instructions for how you can sort files with Proceed.


## setup

If you haven't already, go to WSL, activate our Conda environment for running pipelines, and cd to our folder that contains pipeline definition YAML files.


```
# Activate our Python environment (if not already)
conda activate pipeline-stuff

# Get the latest code
cd /mnt/d/pipelines
```



## initial file conversion step

When sorting a new file, the first step is to convert from Plexon's .plx file format to the raw, binary format expected by Kilosort.

Find a file you want to sort in the "Raw" folder on the Neuropixels machine, for example MM_2022_11_28C_V-ProRec.plx



* from Windows this would look like: D:\data\Raw\MM_2022_11_28C_V-ProRec.plx
* from WSL / Linux this would look like: /mnt/d/data/Raw/MM_2022_11_28C_V-ProRec.plx

[screen shot of Windows file explorer]

[screen shot of WSL terminal "ls" results]

Note the base name of your file -- without the .plx at the end: MM_2022_11_28C_V-ProRec.  You'll need this in all the steps below.  Run the following command, using this plx_name.


```
# Convert plx to kilosort
proceed run plexon-kilosort-phy-fira.yaml --options options.yaml --step-names plx-to-kilosort --args plx_name=MM_2022_11_28C_V-ProRec
```


This will produce several new files in a folder named like the Plexon file, for example:



* D:\data\Kilosort\MM_2022_11_28C_V-ProRec\MM_2022_11_28C_V-ProRec.plx
* D:\data\Kilosort\MM_2022_11_28C_V-ProRec\MM_2022_11_28C_V-ProRec-ops.json

[screen shot of Windows file explorer]

[screen shot of WSL terminal "ls" results]

By default this will convert all channels in the .plx file (even ones without data on them) across the entire file timeline.  You can convert a subset of channels (logical indexing array) and/or a subrange of the recording timeline (in seconds) by passing additional args to the pipeline.


```
# Convert plx to kilosort with specific channels and time range
proceed run plexon-kilosort-phy-fira.yaml --options options.yaml --step-names plx-to-kilosort --args plx_name=MM_2022_11_28C_V-ProRec tStart=120 tEnd=240 channels=[true true false true true false]
```


By default, the conversion will only run once.  Once the output files exist, the pipeline will skip this first step to avoid extra time and work.  You can force the pipeline to re-run the step anyway, by passing a "--force-rerun" flag.

Note: by default Kilosort 3 is hard-coded to work with 10 or more channels, and errors out with fewer than 10.  We [patched the code](https://github.com/benjamin-heasly/Kilosort/pulls?q=is%3Apr+is%3Aclosed) to remove this known limit, and now we can go down to 4 channels.  4 seems to be a harder limit, going deeper into the Kilosort 3 implementation, which would be harder and riskier to patch.  For now, we let's just include 4 or more channels, even if some of those channels end up being empty.


```
# Convert plx to kilosort with force rerun
proceed run plexon-kilosort-phy-fira.yaml --options options.yaml --step-names plx-to-kilosort --args plx_name=MM_2022_11_28C_V-ProRec tStart=120 tEnd=240 channels=[true true false true true false] --force-rerun
```


At this point, you might want to edit some of the values in the generated "MM_2022_11_28C_V-ProRec-ops.json" file.  These values are passed on to Kilosort as its [ops struct](https://github.com/MouseLand/Kilosort/blob/main/configFiles/StandardConfig_MOVEME.m).  If you know what you want already, you can edit these ops before running Kilosort in the next step.

[double check YAML step and args for conversion]


## sorting steps: Kilosort and Phy

Once you convert your file to Kilosort's binary format, you can run Kilosort and view the sorting results in the Phy GUI.  This uses the same pipeline as before, and runs all the steps instead of just the first step.  It will detect that the first step is already done, and skip it.

You can provide a "results_name" arg to the pipeline to have the Kilosort results go to a specific subfolder.  In this example, the subfolder will be named "mysubfolder".


```
proceed run plexon-kilosort-phy-fira.yaml --options options.yaml --args plx_name=MM_2022_11_28C_V-ProRec results_name=mysubfolder
```


After several minutes of sorting, this should open the Phy GUI for an interactive session.

I don't know if having an interactive step is a good or bad idea -- just something we can try!


## revisiting results later on: Phy

In case you come back later to view previous sorting results, you can re-run the whole pipeline as in the previous command.  The pipeline runner should skip the first, completed steps and jump to the interactive Phy GUI step.

You can also run the Phy GUI step explicitly, by name.


```
proceed run plexon-kilosort-phy-fira.yaml --options options.yaml --args plx_name=MM_2022_11_28C_V-ProRec results_name=mysubfolder --step-names "phy gui"
```



# Viewing Plexon Manual Sorting with Phy

We also have a shorter pipeline to convert manually sorted Plexon data to Phy for visualization there.  Run the following in WSL.


```
proceed run plexon-phy.yaml --options options.yaml --args plx_name=MM_2022_11_28C_V-ProRec
```


This will also take several minutes to run and will end with an interactive Phy session.

As above, you can optionally select specific channels and/or time range, and/or for re-conversion of the original .plx file.


```
# Convert plx to kilosort with specific channels and time range
proceed run plexon-phy.yaml --options options.yaml --args plx_name=MM_2022_11_28C_V-ProRec tStart=120 tEnd=240 channels=[true true false true true false]
```


[double check YAML step and args for conversion]


# Summarizing Pipeline Runs

Proceed can also summarize previous pipeline runs into a csv / spreadsheet.

To summarize everything we've tried running so far, run the following in WSL.


```
# Activate our Python environment (if not already)
conda activate pipeline-stuff

# Get the latest code
cd /mnt/d/pipelines
proceed summarize
```


By default this produces a summary in `/mnt/d/pipelines/summary.csv`. You can specify an alternate output file using proceed `summarize --summary-file other.csv`.

It should be possible to view these with Excel, Google Sheets, and/or Libreoffice Calc.  I installed Libreoffice, but annoyingly I can't see any content in the application windows, via NoMachine.  So I've been copying the files to my local machine and viewing them in my own Google Sheets.  Here's an example summary from the Neuropixels machine: [summary.csv](https://docs.google.com/spreadsheets/d/1HXPk-uHdKsgWIrMoRMwV-SRB1duOzGZwgYedrpKH43U/edit?usp=sharing).
