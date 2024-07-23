from typing import Dict, Tuple, List
from pathlib import Path
import json
from session_grv2grv_pipeline_utils import (pre_process_midi_file_and_save, 
                                            post_process_midi_file_and_save)
from groove2groove_wrapper import run_groove2groove, Groove2GrooveModelName, get_groove2groove_metrics

# run self blend

def create_self_blend_per_part(midi_path: str, 
                               structure_xls_path: str,
                               output_folder: str,
                               required_parts: List[str] = [],
                               auto_map_midi = True,
                               groove2groove_temperature:float = 0.4,
                               groove2groove_model: Groove2GrooveModelName = Groove2GrooveModelName.V01_DRUMS,
                               replace_if_file_exist = True,
                               verbose=True, 
                               python_grv2grv_full_link='/home/ubuntu/.conda/envs/groove2groove5/bin/python'):

    split_drums = True
    no_drum_part_name_extention = '_no_drum'
    drum_part_name_extention = '_only_drum'
    grv2grv_extention = (('D' if 'drum' in str(groove2groove_model) else '') + ('V' if 'vel' in str(groove2groove_model) else '') + 
                         '_' + str(groove2groove_temperature).replace('.','')) 
    
    post_processing_extention = '_self_blended'

    
    # for fixing bpm  
    replace_bpm = True
    # define preprocess output folder
    preprocess_out_folder = Path(output_folder) / 'temp'

   # run pre_processing + save files
    saved_path_list = pre_process_midi_file_and_save(midi_path, structure_xls_path, preprocess_out_folder, 
                                                     required_parts=required_parts,
                                                     auto_map_midi=auto_map_midi, split_drum = split_drums, 
                                                     replace_if_file_exist=replace_if_file_exist, verbose=verbose)
    
    bpm_path = [p for p in saved_path_list if p.endswith('.bpm.txt')][0]
    program_dict_path = [p for p in saved_path_list if p.endswith('.program_dict.json')][0]

    for midi_file_part_no_drum in saved_path_list:
        if midi_file_part_no_drum.endswith(f'{no_drum_part_name_extention}.mid'):
            midi_grv2grv_out_path = Path(preprocess_out_folder) / f"{Path(midi_file_part_no_drum).stem}.X.{Path(midi_file_part_no_drum).stem}.{grv2grv_extention}.mid" 
    
            # run groove2groove with the files
            run_groove2groove(midi_file_part_no_drum, midi_file_part_no_drum, midi_grv2grv_out_path, model_name=groove2groove_model, 
                              temperature=groove2groove_temperature, python_grv2grv_full_link=python_grv2grv_full_link)    
            
            # run evaluation with the files
            metrics = get_groove2groove_metrics(midi_file_part_no_drum, midi_file_part_no_drum, midi_grv2grv_out_path)
            # save metrics json

            # run prost process
            drum_midi_path = midi_file_part_no_drum.replace(f'{no_drum_part_name_extention}.mid',f'{drum_part_name_extention}.mid')

            post_processing_output_midi_path = Path(output_folder) / Path(midi_file_part_no_drum).name.replace(no_drum_part_name_extention, post_processing_extention)
            post_process_midi_file_and_save(midi_grv2grv_out_path=midi_grv2grv_out_path, 
                                            post_processing_output_midi_path=post_processing_output_midi_path,
                                            automap_back=auto_map_midi,
                                            program_dict_path=program_dict_path,
                                            add_orig_drum=split_drums and Path(drum_midi_path).exists(),
                                            drum_midi_path=drum_midi_path,
                                            replace_bpm=replace_bpm,
                                            bpm_path=bpm_path,
                                            replace_if_file_exist=replace_if_file_exist,
                                            verbose=verbose)
            
    if verbose:
        print('Done!')


def create_grv2grv_blend_of_different_inputs_per_part():
    pass

if __name__ == '__main__':
    midi_path = "data/sync/data_for_sync/HitCraft_All_Files_Bank_Thin/Black Music Projects/Sub - Genre Afrobeat/57 Afrobeat #1 In F#m/Exports/57 Afrobeat #1 In F#m.midi" 
    structure_xls_path = "data/sync/data_for_sync/HitCraft_All_Files_Bank_Thin/Black Music Projects/Sub - Genre Afrobeat/57 Afrobeat #1 In F#m/Exports/57 Afrobeat #1 In F#m St.xlsx" 
    output_folder = "/home/ubuntu/out_folder_test1"
    create_self_blend_per_part(midi_path=midi_path, structure_xls_path=structure_xls_path, output_folder=output_folder)