# gold-lab-nwb-conversions
Scripts and pipeline definitions for ecephys, sorting, and behavior conversions to nwb

# WIP
Collecting some startup syntax here, while I bootstrap this repo.

[Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)

```
git clone https://github.com/benjamin-heasly/gold-lab-nwb-conversions
cd gold-lab-nwb-conversions

conda env create -f environment.yml
# so slow
conda env update -f environment.yml --prune
# as I learn dependencies better

conda activate gold_nwb
python nwb_plx_poc.py
# runs OK for now

jupyter notebook
# browse to nwb_panel.ipynb
# open local .nwb file like MM_2022_08_05_Rec-tentative-3units.nwb
# runs OK for now
```

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
