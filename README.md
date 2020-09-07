# Groove2Groove

This is the source code for the paper *Groove2Groove: One-Shot Music Style Transfer with Supervision from Synthetic Data*. If you use the code in your research, please cite the paper:
> O. Cífka, U. Şimşekli and G. Richard, "Groove2Groove: One-Shot Music Style Transfer with Supervision from Synthetic Data," in *IEEE/ACM Transactions on Audio, Speech, and Language Processing*, doi: [10.1109/TASLP.2020.3019642](https://doi.org/10.1109/TASLP.2020.3019642).

## Links

[:microscope: Paper postprint](https://hal.archives-ouvertes.fr/hal-02923548)  
[:musical_keyboard: Supplementary website](https://groove2groove.telecom-paris.fr/) with examples and a live demo  
[:musical_note: Examples on YouTube](https://www.youtube.com/playlist?list=PLPdw6Kin7U86tcz-vlMmKqQmq4yL325aH)  
[:file_folder: MIDI file dataset](https://doi.org/10.5281/zenodo.3957999)  

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
