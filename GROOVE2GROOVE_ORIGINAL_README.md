# Groove2Groove

This is the source code for the IEEE TASLP paper:
> Ondřej Cífka, Umut Şimşekli and Gaël Richard. "Groove2Groove: One-Shot Music Style Transfer with Supervision from Synthetic Data." *IEEE/ACM Transactions on Audio, Speech, and Language Processing*, 28:2638–2650, 2020. doi: [10.1109/TASLP.2020.3019642](https://doi.org/10.1109/TASLP.2020.3019642).

If you use the code in your research, please reference the paper.

### Links

[:microscope: Paper postprint](https://hal.archives-ouvertes.fr/hal-02923548) [[pdf](https://hal.archives-ouvertes.fr/hal-02923548/document)]  
[:musical_keyboard: Supplementary website](https://groove2groove.telecom-paris.fr/) with examples and a live demo  
[:musical_note: Examples on YouTube](https://www.youtube.com/playlist?list=PLPdw6Kin7U86tcz-vlMmKqQmq4yL325aH)    
[:file_folder: MIDI file dataset](https://doi.org/10.5281/zenodo.3957999), containing almost 3000 different styles  
[:robot: Band-in-a-Box automation scripts](https://github.com/cifkao/pybiab) for generating the dataset  
[:brain: Model parameters](https://groove2groove.telecom-paris.fr/data/checkpoints/) (to be extracted into [`experiments`](./experiments))


## Looking around

- [`code`](./code): the main codebase (a Python package called `groove2groove`)
- [`data`](./data): scripts needed to prepare the datasets
- [`experiments`](./experiments): experiment configuration files
- [`experiments/eval`](./experiments/eval): evaluation code (see the [`eval.ipynb`](./experiments/eval/eval.ipynb) notebook)
- [`api`](./api): an API server for the web demo

## Installation

Clone the repository, then run the following commands.

1. Install the dependencies using one of the following options:

   -  Create a new environment using conda:
      ```sh
      conda env create -f environment.yml
      ```
      This will also install the correct versions of Python and the CUDA and CuDNN libraries.
   
   -  Using pip (a virtual environment is recommended):
      ```sh
      pip install -r requirements.txt
      ```
      You will need Python 3.6 because we use a version of TensorFlow which is not available from PyPI for more recent Python versions.

   The code has been tested with TensorFlow 1.12, CUDA 9.0 and CuDNN 7.6.0. Other versions of TensorFlow (1.x) may work too.

2. Install the package with:
   ```sh
   pip install './code[gpu]'
   ```
## Usage

The main entry point of the package is the `groove2groove.models.roll2seq_style_transfer` module, which takes care of training and running the model. Run `python -m groove2groove.models.roll2seq_style_transfer -h` to see the available command line arguments.

The `train` command runs the training:
```sh
python -m groove2groove.models.roll2seq_style_transfer --logdir $LOGDIR train
```
Replace `$LOGDIR` with the model directory, containing the `model.yaml` configuration file (e.g. one of the directories under [`experiments`](./experiments)).

To run a trained model on a single pair of MIDI files, use the `run-midi` command, e.g.:
```sh
python -m groove2groove.models.roll2seq_style_transfer --logdir $LOGDIR run-midi \
    --sample --softmax-temperature 0.6 \
    content.mid style.mid output.mid
```

To run it on a whole pre-processed dataset (e.g. the one in [`data/bodhidharma`](./data/bodhidharma)), use the `run-test` command, e.g.:
```sh
python -m groove2groove.models.roll2seq_style_transfer --logdir $LOGDIR run-test \
    --sample --softmax-temperature 0.6 --batch-size 128 \
    content.db style.db keypairs.tsv output.db 
```
Here, `keypairs.tsv` lists on each line a key from `content.db` and a key from `style.db` to use as inputs. Note that `content.db` and `style.db` may be the same file.

## Acknowledgment
This work has received funding from the European Union’s Horizon 2020 research and innovation programme under the Marie Skłodowska-Curie grant agreement No. 765068.

## Copyright notice
Copyright 2019–2020 Ondřej Cífka of Télécom Paris, Institut Polytechnique de Paris.  
All rights reserved.
