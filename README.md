# gold-lab-nwb-conversions
Scripts and pipeline definitions for ecephys, sorting, and behavior conversions to nwb

# WIP
Collecting some startup syntax here, while I bootstrap this repo.

[Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)

```
git clone https://github.com/benjamin-heasly/gold-lab-nwb-conversions
cd gold-lab-nwb-conversions

# this can be slow
conda env create -f environment.yml

# this is useful as I learn and capture dependencies better
conda env update -f environment.yml --prune

# this is also useful sometimes
conda remoev -n gold_nwb --all

# then we can start using the environment
# DON'T FORGET TO ACTIVATE THE ENVIRONMENT :-)
conda activate gold_nwb

jupyter notebook
# browse to nwb_panel.ipynb
# open local .nwb file like MM_2022_08_05_Rec-tentative-3units.nwb
# runs OK for now
```

At the moment pyneo 0.12.0, which reads Plexon files for us, eats so much memory it crushes my laptop (10+ GB of memory for a 1.1 GB file!).
I submitted a PR to reduce this, which they accepted.
When pyneo 0.12.1 is available, we can just update environment.yml to use that version.
In the meantime, I'll manually replace 0.12.0 with the latest from git

    # https://github.com/NeuralEnsemble/python-neo.git

# Related

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
