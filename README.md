# gold-lab-nwb-conversions
Scripts and pipeline definitions for ecephys, sorting, and behavior conversions to nwb

# Conda environment setup
We have a [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) environment called `gold_nwb` defined here in `environment.yml`.  If you create this environment locally and activate it, you should be all set to work with the projects here in this repo, including Jupyter notebooks, Pyramid, etc.

Here are some commands for setting up the Conda environment.

```
# get this repo
git clone https://github.com/benjamin-heasly/gold-lab-nwb-conversions
cd gold-lab-nwb-conversions

# create a fresh environment -- can take several minutes
conda env create -f environment.yml

# if the environment definition has changed, you can update your environment
conda env update -f environment.yml --prune

# you can also delete the environment and start fresh
conda remove -n gold_nwb --all

# don't forget to ACTIVATE the environment before trying to use stuff
conda activate gold_nwb
```

# Related
Here are a few related repos that we've been working on for the Gold lab.

## this repo

 - https://github.com/benjamin-heasly/gold-lab-nwb-conversions

## repose used indirectly from here

 - https://github.com/benjamin-heasly/proceed
 - https://github.com/benjamin-heasly/plx-to-kilosort
 - https://github.com/benjamin-heasly/kilosort3-docker
 - https://github.com/benjamin-heasly/Kilosort
 - https://github.com/benjamin-heasly/phy-to-fira

## scenery we learned about, we might revisit

 - https://github.com/benjamin-heasly/spikeglx-tools-poc
 - https://github.com/benjamin-heasly/signac-poc
