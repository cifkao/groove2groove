from typing import Dict, Tuple, List
import sys
from pathlib import Path
import argparse
from session_grv2grv_pipeline_utils import pre_process_midi_file_and_save, post_process_midi_file_and_save
from groove2groove_wrapper import run_groove2groove, Groove2GrooveModelName, run_groove2groove_evaluation_script

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

    """Util function for creating a self-blend per part of a MIDI file using groove2groove.
    Self blend involves partition of the MIDI to parts (according to a given xls), splitting drums, 
    sequential midi mapping, running groove2groove for each part with itself, midi mapping back, adding the original drums,
    and possibly restoring the BPM value of the original part. Temporary files are saved under 'temp' subfolder of the output folder, 
    while the final self_blend output in a given output_folder.

    :param midi_path: Path to the input MIDI file.
    :param structure_xls_path: Path to the Excel file containing the parts' structure in Session42 format, 
                               which includes part valid name, start bar, and end bar.
    :param output_folder: Desired output folder for the self-blend outputs. Temporary files will be saved under 'temp' sub-folder.
    :param required_parts: List of strings specifying the required structure parts to be processed. 
                           If an empty list is given, use all the parts in the structure xls.
    :param auto_map_midi: Bool flag for enabling sequential MIDI program number mapping 
                          (used to overcome plug-in problems for MIDI files without program mapping).
    :param groove2groove_temperature: Float between 0-1, groove2groove model temperature parameter. Higher = more random output.
    :param groove2groove_model: Groove2GrooveModelName or string, specifying the groove2groove model to use (v01_drums_vel, v01_drums, etc.).
    :param replace_if_file_exist: Bool flag. If True and output file exists, replace it with the new version.
    :param verbose: Bool flag. If True, print more information to the terminal.
    :param python_grv2grv_full_link: Path to the Python executable with matching environment for groove2groove.
    """

    split_drums = True
    no_drum_part_name_extension = '_no_drum'
    drum_part_name_extension = '_only_drum'
    grv2grv_extension = (('D' if 'drum' in str(groove2groove_model) else '') + ('V' if 'vel' in str(groove2groove_model) else '') + 
                         '_T' + str(groove2groove_temperature).replace('.','')) 
    
    post_processing_extension = '_self_blended'

    # for fixing bpm  
    replace_bpm = False
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
        if midi_file_part_no_drum.endswith(f'{no_drum_part_name_extension}.mid'):
            midi_grv2grv_out_path = Path(preprocess_out_folder) / f"{Path(midi_file_part_no_drum).stem}.X.{Path(midi_file_part_no_drum).stem}.{grv2grv_extension}.mid" 

            if replace_if_file_exist or not midi_grv2grv_out_path.exists():
            #TODO WHAT IF FILES EXIST?
            # run groove2groove with the files
                run_groove2groove(midi_file_part_no_drum, midi_file_part_no_drum, midi_grv2grv_out_path, model_name=groove2groove_model, 
                                temperature=groove2groove_temperature, python_grv2grv_full_link=python_grv2grv_full_link, verbose=verbose)
            elif verbose:
                print(f"groove2groove output {midi_grv2grv_out_path} exists, skipping groove2groove run...")   
            
            analysis_out_path = Path(preprocess_out_folder) / midi_grv2grv_out_path.stem.replace(grv2grv_extension, 'analysis.json')
            # run evaluation with the files
            if replace_if_file_exist or not analysis_out_path.exists():
                run_groove2groove_evaluation_script(midi_file_part_no_drum, midi_file_part_no_drum, midi_grv2grv_out_path, 
                                                    analysis_out_path = analysis_out_path,
                                                    model_name=groove2groove_model,  temperature=groove2groove_temperature, 
                                                    python_grv2grv_full_link=python_grv2grv_full_link, verbose=verbose)
            elif verbose:
                print(f"groove2groove evaluation file {analysis_out_path} exists, skipping groove2groove evaluation run...")  

            # run prost process
            drum_midi_path = midi_file_part_no_drum.replace(f'{no_drum_part_name_extension}.mid',f'{drum_part_name_extension}.mid')
            post_processing_output_midi_path = Path(output_folder) / Path(midi_file_part_no_drum).name.replace(no_drum_part_name_extension, post_processing_extension)
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


def parse_arguments():
    "Parser for the arguments of create_self_blend_per_part"
    parser = argparse.ArgumentParser(description="Create self-blend per part of a MIDI file using groove2groove.")
    parser.add_argument("midi_path", type=str, help="Path to the input MIDI file.")
    parser.add_argument("structure_xls_path", type=str, help="Path to the Excel file containing the parts' structure in Session42 format.")
    parser.add_argument("output_folder", type=str, help="Desired output folder for the self-blend outputs.")
    parser.add_argument("--required_parts", type=str, nargs='*', default=[], 
                        help="List of required structure parts to be processed. If empty, use all parts.")
    parser.add_argument("--auto_map_midi", type=bool, default=True, 
                        help="Enable sequential MIDI program number mapping.")
    parser.add_argument("--groove2groove_temperature", type=float, default=0.4, 
                        help="Groove2groove model temperature parameter.")
    parser.add_argument("--groove2groove_model", type=str, default=Groove2GrooveModelName.V01_DRUMS.value, 
                        choices=[model.value for model in Groove2GrooveModelName], 
                        help="Groove2groove model to use.")
    parser.add_argument("--replace_if_file_exist", type=bool, default=True, 
                        help="Replace the file if it exists.")
    parser.add_argument("--verbose", type=bool, default=True, 
                        help="Print more information to the terminal.")
    parser.add_argument("--python_grv2grv_full_link", type=str, default='/home/ubuntu/.conda/envs/groove2groove5/bin/python', 
                        help="Path to the Python executable with matching environment for groove2groove.")
    
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    if len(sys.argv) > 1:
        args = parse_arguments()
        create_self_blend_per_part(
            midi_path=args.midi_path,
            structure_xls_path=args.structure_xls_path,
            output_folder=args.output_folder,
            required_parts=args.required_parts,
            auto_map_midi=args.auto_map_midi,
            groove2groove_temperature=args.groove2groove_temperature,
            groove2groove_model=Groove2GrooveModelName(args.groove2groove_model),
            replace_if_file_exist=args.replace_if_file_exist,
            verbose=args.verbose,
            python_grv2grv_full_link=args.python_grv2grv_full_link)

    else:
        # TODO: get rid of this - NATAN - Maybe add example files?
        print('NO arguments were given, using a default')
        midi_path = "data/sync/data_for_sync/HitCraft_All_Files_Bank_Thin/Black Music Projects/Sub - Genre Afrobeat/57 Afrobeat #1 In F#m/Exports/57 Afrobeat #1 In F#m.midi" 
        structure_xls_path = "data/sync/data_for_sync/HitCraft_All_Files_Bank_Thin/Black Music Projects/Sub - Genre Afrobeat/57 Afrobeat #1 In F#m/Exports/57 Afrobeat #1 In F#m St.xlsx" 
        output_folder = "/home/ubuntu/out_folder_test1"
        create_self_blend_per_part(midi_path=midi_path, structure_xls_path=structure_xls_path, 
                                output_folder=output_folder, verbose=True, replace_if_file_exist=False)