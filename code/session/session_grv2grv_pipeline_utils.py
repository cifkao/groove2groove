"""This file contains util functions that have to do with the pre-processing and post-processing of session midi and excel files,
for generating groove2groove outputs. They focus on name conventions in the structure xls, saving output files, etc.
Most of the functions functionality for editing and changing midi files is found in the session_grv2grv_processing_utils.py util file"""

from typing import Optional, List, Dict, Tuple
from pathlib import Path
import pandas as pd
import json

import music21 as m21

from session_grv2grv_processing_utils import (preprocess_midi_file,
                                              assign_part_name_to_grv2grv_output_midi_stream_by_program_dict, 
                                              replace_drums_in_midi_stream,                                               
                                              assign_bpm_to_midi_stream)


VALID_STRUCTURE_PART_NAMES = ['Verse', 'Verse 1', 'Verse 2', 'Verse 3', 'Verse 4', 'Verse 5', 'Verse 6',
                    'Pre - Chorus', 'Pre - Chorus 1', 'Pre - Chorus 2', 'Pre - Chorus 3', 'Pre - Chorus 4',  'Pre - Chorus 5', 'Pre - Chorus 6',
                    'Chorus', 'Chorus 1', 'Chorus 2', 'Chorus 3', 'Chorus 4', 'Chorus 5', 'Chorus 6', 
                    'Post - Chorus', 'Post - Chorus 1', 'Post - Chorus 2', 'Post - Chorus 3', 'Post - Chorus 4', 'Post - Chorus 5', 'Post - Chorus 6', 
                    'Intro', 'Interlude', 'C - Part', 'Coda', 'Outro', ]


def get_stucture_dict_from_xls(structure_xls_path, 
                               structure_part_names: List[str] = [],
                               fix_part_names=True, 
                               remove_last_char_1_in_part_name=True,
                               ) -> Dict[str, Tuple[int, int]]:
    """util function for extracting a dictionary of structure part names and the start_bar, end_bar 
    from session structure xls.
    :param structure_xls_path: path to the structure xls
    :param structure_part_names: list of str - of specific structure parts required (otherwise takes all)
    :param fix_part_names: bool, to fix the part names to Title case without spaces and dashes.
    :param remove_last_char_1_in_part_name: remove the figure '1' from the end of a part name: example Verse1->Verse
    :return: dictionary with sturcute_part_name as key and (start_bar, end_bar) as value.
    """
        
    if not Path(structure_xls_path).exists():
        print(f'input_structure_xls {structure_xls_path} does not exist')
        return {}

    df_structure = pd.read_excel(structure_xls_path)
    
    for col in ['Part','Startbar','Endbar']:
        if col not in df_structure.columns:
            print(f"column '{col}' not in '{structure_xls_path}'. only {df_structure.columns}")
            return
    df_structure = df_structure[['Part','Startbar','Endbar']].dropna(how='all')

    # remove spaces from part names
    if fix_part_names:
        df_structure['Part_fixed_name'] = df_structure['Part'].str.title().str.replace(' ','').str.replace('-','')
    else:
        df_structure['Part_fixed_name'] = df_structure['Part']
    if remove_last_char_1_in_part_name:
        df_structure['Part_fixed_name'] = df_structure['Part_fixed_name'].apply(lambda x: x[:-1] if x.endswith('1') else x)

    # get dict using the 'Part' name w/o spaces as key and the ('Startbar','Endbar') as values.
    all_struct_first_and_last_bar_dict = df_structure.set_index('Part_fixed_name')[['Startbar', 'Endbar']].astype(int).apply(tuple, axis=1).to_dict()

    if not structure_part_names:
        return all_struct_first_and_last_bar_dict
    
    else:
        partial_struct_first_and_last_bar_dict = {}
        for structure_part_name in structure_part_names:
            name_fixed = structure_part_name.title().replace(' ','').replace('-','') if fix_part_names else structure_part_name

            if name_fixed in all_struct_first_and_last_bar_dict: 
                partial_struct_first_and_last_bar_dict[name_fixed] = all_struct_first_and_last_bar_dict[name_fixed]
            else:
                print(f"Part '{structure_part_name}' not found in '{structure_xls_path}', only: {df_structure['Part'].values}")

        return partial_struct_first_and_last_bar_dict


def find_structure_invalid_names_in_xls(structure_xls_path, 
                                        valid_structure_part_names: List[str] = VALID_STRUCTURE_PART_NAMES,
                                        fix_part_names=False, 
                                        strip_part_names=False, 
                                        verbose=True) -> List[str]:
    """
    :param structure_xls_path: path to the structure xls
    :param valid_structure_part_names: list of str - valid part names
    :param fix_part_names: bool, to fix the part names to Title case without spaces and dashes.
    :param strip_part_names: bool, to strip the part names from spaces at the beginning and end.
    :param verbose: bool, print validation status.
    :return: list of invalid parts.
    """
        
    if not Path(structure_xls_path).exists():
        if verbose:
            print(f'input_structure_xls {structure_xls_path} does not exist')
        return []

    df_structure = pd.read_excel(structure_xls_path)
    
    for col in ['Part','Startbar','Endbar']:
        if col not in df_structure.columns:
            if verbose:
                print(f"column '{col}' not in '{structure_xls_path}'. only {df_structure.columns}")
            return []

    # get rid of NaN rows
    df_structure = df_structure.dropna(how='all', subset=['Part','Startbar','Endbar'])


    # remove spaces from part names
    if fix_part_names:
        df_structure['Part_fixed_name'] = df_structure['Part'].str.title().str.replace(' ','').str.replace('-','')
    elif strip_part_names:
        df_structure['Part_fixed_name'] = df_structure['Part'].str.strip()
    else:
        df_structure['Part_fixed_name'] = df_structure['Part']

    all_struct_first_and_last_bar_dict = df_structure.set_index('Part_fixed_name')[['Startbar', 'Endbar']].astype(int).apply(tuple, axis=1).to_dict()

    if fix_part_names:
        valid_structure_part_names = [p.title().replace(' ','').replace('-','') for p in valid_structure_part_names] 
    
    invalid_part_names = [p for p in all_struct_first_and_last_bar_dict.keys() if p not in valid_structure_part_names]

    
    if invalid_part_names:
        invalid_part_names_str = "'" + "', '".join(invalid_part_names) + "'"
        if verbose:
            print(f"{Path(structure_xls_path).name}\tinvalid: {invalid_part_names_str}")
    return invalid_part_names


def pre_process_midi_file_and_save(input_midi_path: str, structure_xls_path: str, preprocess_out_folder: str, 
                                   required_parts: List[str]=['Verse','Chorus','Pre Chorus'],
                                   auto_map_midi = True, split_drum = True, 
                                   no_drum_part_name_extension: str = '_no_drum',
                                   drum_part_name_extension: str = '_only_drum',
                                   replace_if_file_exist = True, verbose = True,) -> List[str]:
    """
    Util function for pre-processing MIDI files for groove2groove including saving.
    including:  midi files cropped by structure parts (with, without or only drums), 
                json files with program mapping (for midi mapping) and text file with bpm.

    :param input_midi_path: path to midi score to be pre-processed
    :param structure_xls_path: excel with the parts' structure in Session42 format contatining part valid name, start bar and end bar.    
    :param preprocess_out_folder: desired output folder for pre-processing outputs    
    :param required_parts: List of strings - of the required structure parts to be output. if an empty list us given - use all the parts.
    :param auto_map_midi: bool flag for enabling sequential midi program number mapping 
            (used to overcome plug-in problems for midi files without program mapping) 
    :param split_drum: bool flag for splitting the drums to different midi file output.
    :param no_drum_part_name_extention: str, if split_drum is True- this is the extention to be added to the structure part name for the split w/o drums
    :param drum_part_name_extention: str, if split_drum is True- this is the extention to be added to the structure part name for the split containing only drums
    :param replace_if_file_exist: bool flag. if True and output file exist - replace it with the new version.
    :param verbose: bool flag. if True print more information to the terminal.
    :return: list of all the written file paths. 
    """

    # verify that the required files exist:
    if not Path(input_midi_path).exists():
        raise FileNotFoundError(f"MIDI file {input_midi_path} cannot be found.")

    if not Path(structure_xls_path).exists():
        raise FileNotFoundError(f'Structure xls file {structure_xls_path} cannot be found.')

    if not Path(preprocess_out_folder).exists():
        if verbose:
            print(f"Creating pre-processing output folder: '{preprocess_out_folder}'")
        Path(preprocess_out_folder).mkdir(parents=True, exist_ok=True)

    # define list of all the saved path:
    saved_path_list = []

    # get a dictionary with the relevant parts to first and last bar mapping
    part_struct_first_and_last_bar_dict = get_stucture_dict_from_xls(structure_xls_path, required_parts, 
                                                                      remove_last_char_1_in_part_name=True)
    
    # get a stream dictionary (cropped parts w or w/o or only drums, mapping dict etc.)
    stream_dict, program_dict, drum_dict, bpm = preprocess_midi_file(input_midi_path, 
                                                                    part_struct_first_and_last_bar_dict, 
                                                                    auto_map_midi = auto_map_midi, 
                                                                    split_drum = split_drum,
                                                                    no_drum_part_name_extension = no_drum_part_name_extension,
                                                                    drum_part_name_extension = drum_part_name_extension,)
    
    # save files:
    base_name =Path(input_midi_path).stem
    for part_name, midi_stream in stream_dict.items():
        output_midi_file = Path(preprocess_out_folder) / f'{base_name}.{part_name}.mid'
        saved_path_list.append(str(output_midi_file))
        if replace_if_file_exist or not output_midi_file.exists():
            midi_stream.write('midi', fp=output_midi_file)
            if verbose:
                print(f"Preprocessed {part_name} saved to '{output_midi_file}'")

    if program_dict:
        p_json_file_path =  Path(preprocess_out_folder) / (base_name  + '.program_dict.json')
        saved_path_list.append(str(p_json_file_path))
        if replace_if_file_exist or not p_json_file_path.exists():
            # Save the dictionary to a JSON file
            with open(p_json_file_path, 'w') as p_json_file:
                json.dump(program_dict, p_json_file, indent=4)
                if verbose:
                    print(f"Program Dict Dictionary saved to {p_json_file_path}")
    if drum_dict:
        d_json_file_path =  Path(preprocess_out_folder) / (base_name  + '.drum_dict.json')
        saved_path_list.append(str(d_json_file_path))
        if replace_if_file_exist or not d_json_file_path.exists():
            # Save the dictionary to a JSON file
            with open(d_json_file_path, 'w') as d_json_file:
                json.dump(drum_dict, d_json_file, indent=4)
                if verbose:
                    print(f"Drum Dict Dictionary saved to {d_json_file_path}")

    if bpm is not None:
        bpm_path =  Path(preprocess_out_folder) / (base_name  + '.bpm.txt')
        saved_path_list.append(str(bpm_path))
        if replace_if_file_exist or not bpm_path.exists():
            with open(bpm_path, 'w') as file:
                file.write(str(bpm))
                if verbose:
                    print(f"BPM saved to {bpm_path}")
                    
    return saved_path_list


# TODO add explenation
def post_process_midi_file_and_save(midi_grv2grv_out_path:str, 
                                     post_processing_output_midi_path:str, 
                                     automap_back = True,
                                     program_dict_path: Optional[str] = None,
                                     add_orig_drum = True,
                                     drum_midi_path: Optional[str] = None,
                                     replace_bpm = False,
                                     bpm_path: Optional[str] = None,
                                     replace_if_file_exist = True,
                                     verbose = True):
    
    # check if output file exist
    if not replace_if_file_exist and post_processing_output_midi_path.exists():
        if verbose:
            print(f"output post-processes file '{post_processing_output_midi_path}' already exists. skipping")
        return 

    if not Path(midi_grv2grv_out_path).exists():
        FileNotFoundError(f"groove2groove output MIDI file '{midi_grv2grv_out_path}' cannot be found.")

    if automap_back:
        # take the drum file from content #in principle should be from the style:
        if program_dict_path is None or not Path(program_dict_path).exists():
            FileNotFoundError(f"MIDI Program mapping json file '{program_dict_path}' cannot be found.")

    if add_orig_drum:
        if drum_midi_path is None or not Path(drum_midi_path).exists():
            FileNotFoundError(f"DRUM MIDI file '{drum_midi_path}' cannot be found.")

    if replace_bpm:
        if bpm_path is None or not Path(bpm_path).exists():
            print(f"BPM file text '{bpm_path}' cannot be found")

    # create output folder if required
    if not Path(post_processing_output_midi_path).parent.exists():
        if verbose:
            print(f"Creating post-processing output folder: '{Path(post_processing_output_midi_path).parent}'")
        Path(post_processing_output_midi_path).parent.mkdir(parents=True, exist_ok=True)


    # now we can start:
    midi_stream = m21.converter.parse(midi_grv2grv_out_path)

    if automap_back:
        with open(program_dict_path, 'r') as f:
            program_dict = json.load(f)

        midi_stream = assign_part_name_to_grv2grv_output_midi_stream_by_program_dict(midi_stream, program_dict, remove_drum=True)
        if verbose:
            print(f"auto mapping back '{midi_grv2grv_out_path}'")
    
    if add_orig_drum:
        drum_stream = m21.converter.parse(drum_midi_path)

        midi_stream = replace_drums_in_midi_stream(midi_stream, drum_stream)
        if verbose:
            print(f"replacing '{midi_grv2grv_out_path}' drums with '{drum_midi_path}'")

    # replace bpm
    if replace_bpm:
        with open(bpm_path, 'r') as ff:
            bpm = float(ff.read().strip())
            if bpm > 0:
                midi_stream = assign_bpm_to_midi_stream(midi_stream, bpm)
            else:
                ValueError(f'invalid bpm value {bpm} found in file {str(bpm_path)}')

    midi_stream.write('midi', fp=post_processing_output_midi_path)
    if verbose:
        print(f"post-processed midi saved to: '{post_processing_output_midi_path}'")
        