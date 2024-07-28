# Session-Groove2Groove MIDI Blend Utilities
This project provides utilities for pre-processing, post-processing, running groove2groove model, and creating blends and self-blends of MIDI files using the groove2groove model.
It assumes Session42 MIDI inputs, where the instrument name is given as a "MIDI part name", together with xls that contains the division to "structure parts" by bars. 

### Overview - Blend Utility (mixing Contend MIDI and Style MIDI) and Self Blend Utilities.
This project includes two main scripts: 
1. Blending Session42 Content MIDI + Style MIDIs, MIDIs (The MIDIs are split and structure parts with identical name are being "blend" together):
`code/session/session_grv2grv_full_pipeline.py` - for blending parts of different 

2. Self varianter- for creating new variants of MIDI parts (each part is blend with itself). 
`code/session/session_grv2grv_self_blend_pipeline.py` 


The main function within `session_grv2grv_full_pipeline.py` and `code/session/session_grv2grv_self_blend_pipeline.py` is `create_blend_per_part`.
It is used for mixing Content+Style MIDI files using groove2groove, and composed of the foolowing steps:

1. Partitioning the MIDI files into their structure parts (following the given Structure XLS file),
2. Splitting drums (if required, for adding the original drums in the post processing)
3. Naive Sequential MIDI mapping  (if required, for overcoming plugin issues)
4. Running groove2groove per part (each part servers as the `Style MIDI` and as the `Content MIDI` of the original groove2groove model).
5. MIDI Mapping Back (if required, by adding the original instruments names)
6. Adds the original drums (if requested)
7. Possibly restores the BPM value of the original part (if required, for overcoming bugs).

Al the temporary files are saved under a `/temp` subfolder of the specified output folder, while the final self-blend output is saved in the provided output folder.

## Technicalities
### Creating environment and downloading weights:
While groove2groove original model requires python <=3.6 to support deprecated tensorflow, Music21 package requires a newer version. Therefore two python environments must be defined.

The main script should be used from the new python env, while providing the executable to the python3.6 with groove2groove dependencies as a parameter (groove2groove call is done via sub-process with this executable).

Therefore, before running the scripts, the two environments must be build:

```conda env create -f groove2groove_environment.yml```

```conda env create -f session_environment.yml```

```conda activate session```


In addition - groove2groove model weights must be downloaded first. 
This can be done using the utility script, where <model_name> must be one of: `v01_drums`, `v01_drums_vel`, `v01`, `v0_vel` :

```code/session/download_groove2groove_model_weights.sh <model_name>```

### Command Line Usage
You can run the `session_grv2grv_full_pipeline.py` script from the command line using the following script:
```python code/session/session_grv2grv_self_blend_pipeline.py path_to_midi_file path_to_structure_xls output_folder --required_parts part1 part2 --auto_map_midi True --groove2groove_temperature 0.4 --groove2groove_model v01_drums --replace_if_file_exist True --verbose True --python_exe_for_grv2grv_env /path/to/python_executable```

### Parameters:
Mandatory for: `session_grv2grv_self_blend_pipeline.py`:
  * midi_path: Path to the input MIDI file that will be used as input for processing.      
  * structure_xls_path: Path to the Excel file containing the parts' structure in Session42 format.
  * output_folder: Desired output folder for the saving the self-blend outputs. 
    Temporary files will be saved in a sub-folder `temp/`

Mandatory for: `session_grv2grv_full_pipeline.py`:
  * content_midi_path: Path to content MIDI.
  * content_structure_xls_path: Path to Content Structure Excel.
  * style_midi_path: Path to Style MIDI. 
  * style_structure_xls_path:  Path to Style Structure Excel.
  *output_folder: Desired output folder (temporary files will be saved in `/temp` sub-folder)

Additional options for both scripts:      

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




### Additional Notes:
#### Time Signature: 
The current groove2groove model supports only time signature of 4/4. It is possible to edit 3/4 time signature to 4/4 by using triola-legnth notes, but it is not clear what will be the quality of the output. 
#### Drums: 
MIDI mapping of percussion was not handled within this project, therfore for the self blending, the original "Content MIDI" drums are added to the output.
Groove2groove model treats differently pitched instruments (where the midi number signifies pitch) and percussive instruments (where midi number signifies type of instrument). Mapping percussion plug-ins into MIDI numbers is more complicated, since the mapping should involve changing the MIDI Notes numbers. Therefore we currently do not support non-pitched MIDI Mapping.
In principle - the "Style MIDI" drums should be taken into account for preserving the style. But due to non-pitched midi mapping limiation, and the unexpected result when running groove2groove with un-mapped drums, we decided to use the original drums. Moreover, the length of the Style might be different from the length of the Content + Output MIDIs. Therefore we decided to use the Content drums (in the case of self blend the Content and the Style are identical - so it does not matter).

#### MIDI mapping 
The current implementation support Sequential MIDI mapping to overcome plug-in issues, and run groove2groove correctly. The sequential MIDI program numbers are mapped back at the post-processing stage. Mixing songs with mapping and songs without is currnly not supported.
