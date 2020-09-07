Data preparation
================

This directory contains scripts and other files needed to prepare the training and test datasets.
Before starting, make sure that the `groove2groove` package is installed in your environment.

The scripts will download the data and perform some preprocessing. This includes conversion to the format
used by Groove2Groove: an [LMDB](https://lmdb.readthedocs.io/) database of
[Magenta note sequences](https://github.com/magenta/note-seq) plus a JSON file with metadata.

Synthetic data
--------------
1. Go to the `synth` directory and run `./download.sh`. This will download the synthetic dataset from
[Zenodo](http://doi.org/10.5281/zenodo.3958000) and extract the relevant files to the `train`, `val`
and `test` subdirectories.
2. Preprocess each part of the dataset:
   ```
   ./prepare.sh train
   ./prepare.sh val
   ./prepare.sh test
   ```

Bodhidharma
-----------
Go to the `bodhidharma` directory and run `./prepare.sh`. This will download, extract and preprocess
the dataset.

Additionally, velocity normalization needs to be performed by running the [`vel_norm.ipynb`](./vel_norm.ipynb) notebook.
