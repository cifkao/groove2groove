# Groove2Groove

This is the source code for the paper:
> Ondřej Cífka, Umut Şimşekli and Gaël Richard. "Groove2Groove: One-Shot Music Style Transfer with Supervision from Synthetic Data." *IEEE/ACM Transactions on Audio, Speech, and Language Processing*, 28:2638–2650, 2020. doi: [10.1109/TASLP.2020.3019642](https://doi.org/10.1109/TASLP.2020.3019642).

If you use the code in your research, please reference the paper.

### Links

[:microscope: Paper postprint](https://hal.archives-ouvertes.fr/hal-02923548) [[pdf](https://hal.archives-ouvertes.fr/hal-02923548/document)]  
[:musical_keyboard: Supplementary website](https://groove2groove.telecom-paris.fr/) with examples and a live demo  
[:musical_note: Examples on YouTube](https://www.youtube.com/playlist?list=PLPdw6Kin7U86tcz-vlMmKqQmq4yL325aH)  
[:file_folder: MIDI file dataset](https://doi.org/10.5281/zenodo.3957999)  


## Looking around

- [`code`](./code): the main codebase (a Python package called `groove2groove`)
- [`data`](./data): scripts needed to prepare the datasets
- [`experiments`](./experiments): experiment configuration files
- [`api`](./api): an API server for the web demo
- evaluation code still needs to be added

## Installation

Clone the repository and make sure you have Python 3.6 or later. Then run the following commands.

1. (optional) If you use conda, you can create your environment using
   ```sh
   conda env create -f environment.yml
   ```
   This will also install the correct versions of the CUDA and CuDNN libraries.
   
2. Install requirements:
   ```sh
   pip install -r requirements.txt
   ```

3. Install the package with:
   ```sh
   pip install './code[gpu]'
   ```
## Usage

The main entry point of the package is the `groove2groove.models.roll2seq_style_transfer` module, which takes care of training and running the model. Run `python -m groove2groove.models.roll2seq_style_transfer -h` to see the available command line arguments.

The `train` command runs the training, replacing `$LOGDIR` with the directory containing the `model.yaml` configuration file (e.g. one of the directories under [`experiments`](./experiments)):
```sh
python -m groove2groove.models.roll2seq_style_transfer --logdir $LOGDIR train
```

To run the trained model on a single pair of MIDI files, use the `run-midi` command, e.g.:
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
