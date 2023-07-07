# Pyramid

This folder contains a Python project called Pyramid.
"Pyramid" is a pun on "Python" and "FIRA" (the Gold Lab's long-standing Matlab analysis tools).
Pyramid is intended as a successor to FIRA.

Pyramid reads data from various sources into a simple, shared data model called the Neutral Zone.
Based on event times in the Neutral Zone, it delimits Trials in time.
It populates each trial with data from various sources, configured by a YAML file.
It produces a JSON "trial file" with one big array of trials.

Pyramid can run online as an experiment happens or offline for later data analysis.
Either way, it views data as a sliding window over time.
This approach is helpful for dealing with live data as well as large data files.

Pyramid is a work in progress, but here's an overview of the vision.

![Pyramid reads data into the Neutral Zone and delimits and extracts Trials.](docs/pyramid-sketch-Page-1.png "Pyramid overview")

# Demos 

Please see some demos, each with its own README:
 - [core functionality](docs/core-demo/README.md)
 - [signals](docs/signal-demo/README.md)

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

If you've already dones that in the past but you want to make sure you're up to date, you can update your conda environment.

```
cd gold-lab-nwb-conversions
git pull
conda env update -f environment.yml --prune
```

## pyramid

Now you can install Pyramid from this repo into the `gold_nwb` environment on your machine.

```
cd pyramid
conda activate gold_nwb
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
