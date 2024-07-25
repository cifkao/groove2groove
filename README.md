# Session-Groove2Groove MIDI Blend Utilities
This project provides utilities for pre-processing, post-processing, running groove2groove model, and creating blends and self-blends of MIDI files using the groove2groove model.

## Overview - Blend Utility (mixing Contend MIDI and Style MIDI) and Self Blend Utilities.
This project includes two main scripts: 
`code/session/session_grv2grv_full_pipeline.py` - for blending parts of different Content + Style MIDIs, 
and `code/session/session_grv2grv_self_blend_pipeline.py` - for creating new variants of MIDI parts (with themselves).


The main function within `session_grv2grv_full_pipeline.py` is `create_self_blend_per_part`, which divides the MIDI files to their parts (as given in Session Format structure xls file), splits the drums (if required), performs naive sequential MIDI mapping (if required, for overcoming plugin issues), then runs groove2groove model for per part (each part servers as the `Style MIDI` and as the `Content MIDI`), maps MIDI back by adding the original instruments names (if required), adds original drums (if requested), and possibly restores the BPM value of the original part.

Temporary files are saved under a `temp` subfolder of the specified output folder, while the final self-blend output is saved in the provided output folder.

## Technicalities
While groove2groove original model requires python <=3.6 to support deprecated tensorflow, Music21 package requires a newer version. Therefore two python environments must be defined.

The main script should be used from the new python env, while providing the executable to the python3.6 with groove2groove dependencies as a parameter (groove2groove call is done via sub-process with this executable).

Therefore, before running the scripts, the two environments should be build:

```conda env create -f groove2groove_environment.yml```
```conda env create -f session_environment.yml```
```conda activate session```

In addition - groove2groove model weights must be downloaded first. This can be done using the utility script: 
```code/session/download_groove2groove_model_weights.sh <model_name>```
where model_name is one of: v01_drums, v01_drums_vel, v01, v0_vel

### Description

Util function for creating a self-blend per part of a MIDI file using groove2groove. Self-blend involves partitioning the MIDI into parts (according to a given XLS), splitting drums, sequential MIDI mapping, running groove2groove for each part with itself, MIDI mapping back, adding the original drums, and possibly restoring the BPM value of the original part.


## Command Line Usage
You can run the `session_grv2grv_full_pipeline.py` script from the command line using the following script:
```python session_grv2grv_full_pipeline.py path_to_midi_file path_to_structure_xls output_folder --required_parts part1 part2 --auto_map_midi True --groove2groove_temperature 0.4 --groove2groove_model v01_drums --replace_if_file_exist True --verbose True --python_exe_for_grv2grv_env /path/to/python_executable```

### parameters:
Mandatory:
  midi_path: Path to the input MIDI file that will be used as input for processing.      
  structure_xls_path: Path to the Excel file containing the parts' structure in Session42 format.
  output_folder: Desired output folder for the saving the self-blend outputs. 
    Temporary files will be saved in a sub-folder temp

Additional options:      
  --required_parts: List of the required structure part names to be processed. If empty, use all parts. (Default = [] empty for using all parts)
  
  --auto_map_midi: Boolean flag for enabling sequential MIDI program number mapping (this is relevant for Session MIDIs with Plug-ins only). 
      When set to True, this will enable automatic sequential mapping of MIDI program numbers by the part-instrument names. Default=True.
      For non-Session MIDIs - should be set to False. (Default = True)
  
  --groove2groove_temperature: The temperature parameter for the groove2groove model, between 0-1. default=0.4. controls the randomness of the model's output.

  --groove2groove_model: Groove2groove model to use ('v01_drums', 'v01_drums_vel', 'v01', 'v01_vel'). 
      Specifies which groove2groove model to use for processing. Available models are listed as choices. (Default = 'v01_drums') 
      Note that the required models should be downloaded first. 

  --replace_if_file_exist: Replace the file if it exists. 
  If set to True, the output file will be replaced if it already exists in the specified output folder. (Default = True)

  --verbose: Flag for enabling verbose mode, which provides additional details during execution. (Default = True)

  --python_exe_for_grv2grv_env: Path to the Python executable that has the appropriate environment for running groove2groove. (Default='/home/ubuntu/.conda/envs/groove2groove/bin/python')




