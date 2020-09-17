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

## Acknowledgment
This work has received funding from the European Union’s Horizon 2020 research and innovation programme under the Marie Skłodowska-Curie grant agreement No. 765068.

## Copyright notice
Copyright 2019–2020 Ondřej Cífka of Télécom Paris, Institut Polytechnique de Paris.  
All rights reserved.
