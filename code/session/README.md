# MIDI Self-Blend Utility

This project provides utilities for pre-processing, post-processing, running groove2groove model, and creating self-blends of MIDI files using the groove2groove model.
The main script: `code/session/session_grv2grv_full_pipeline.py`
Is used for creating variants for each part of the MIDI, following the structure in a given structure xls file. 

## Overview - Self-Blend Utility

The main function within `session_grv2grv_full_pipeline.py` is `create_self_blend_per_part`, which divides the midi to its parts, then split the drums (if required), performing naive sequential midi mapping (if required, for overcoming plugin issues), then run groove2groove model for each part (each part servers as the `style midi` and as the `content midi`), mapping MIDI back by adding the original instruments names (if required), adding original drums (if requested), and possibly restoring the BPM value of the original part.

Temporary files are saved under a `temp` subfolder of the specified output folder, while the final self-blend output is saved in the provided output folder.


## Technicalities
While groove2groove original model requires python <=3.6 to support deprecated tensorflow, Music21 package requires a newer version. Therefore two python environments must be defined.
The main script should be used from the new python env, while providing the executable to the python3.6 with groove2groove dependencies as a parameter (groove2groove call is done via sub-process with this executable).

Therefore, before running the scripts, the two environments should be build.

In addition - groove2groove model weights should be downloaded. For this you may use the utility script: 
`code/session/download_groove2groove_model_weights.sh`


### Description

Util function for creating a self-blend per part of a MIDI file using groove2groove. Self-blend involves partitioning the MIDI into parts (according to a given XLS), splitting drums, sequential MIDI mapping, running groove2groove for each part with itself, MIDI mapping back, adding the original drums, and possibly restoring the BPM value of the original part.


## Command Line Usage
You can run the `session_grv2grv_full_pipeline.py` script from the command line using the following script:
```python session_grv2grv_full_pipeline.py path_to_midi_file path_to_structure_xls output_folder --required_parts part1 part2 --auto_map_midi True --groove2groove_temperature 0.4 --groove2groove_model v01_drums --replace_if_file_exist True --verbose True --python_grv2grv_full_link /path/to/python_executable```

### parameters:
Mandatory:
  midi_path: Path to the input MIDI file that will be used as input for processing.      
  structure_xls_path: Path to the Excel file containing the parts' structure in Session42 format.
  output_folder: Desired output folder for the saving the self-blend outputs. 
    Temporary files will be saved in a sub-folder temp

Additional options:      
  --required_parts: List of the required structure part names to be processed. If empty, use all parts.
  
  --auto_map_midi: Boolean flag for enabling sequential MIDI program number mapping.
      When set to True, this will enable automatic sequential mapping of MIDI program numbers.
  
  --groove2groove_temperature: The temperature parameter for the groove2groove model, between 0-1. default=0.4. controls the randomness of the model's output.

  --groove2groove_model: Groove2groove model to use ('v01_drums', 'v01_drums_vel', 'v01', 'v01_vel') default is 'v01_drums'.
      Specifies which groove2groove model to use for processing. Available models are listed as choices. 
      Note that while 'v01_drums', 'v01_drums_vel' can be downloaded via the preperation script, 'v01' and 'v01_vel' should be downloaded seperatly if desired. 

  --replace_if_file_exist (bool, default=True): Replace the file if it exists.
      If set to True, the output file will be replaced if it already exists in the specified output folder.

  --verbose (bool, default=True): Print more information to the terminal.
      Enables verbose mode, which provides additional details during execution.

  --python_grv2grv_full_link (str, default='/home/ubuntu/.conda/envs/groove2groove/bin/python'): Path to the Python executable with matching environment for groove2groove.
      This specifies the path to the Python executable that has the appropriate environment for running groove2groove.
