from typing import List, Optional
import sys
from pathlib import Path
import argparse
from session_grv2grv_full_pipeline import create_blend_per_part
from groove2groove_wrapper import Groove2GrooveModelName

# run self blend

def create_self_blend_per_part(midi_path: str, 
                               structure_xls_path: str,
                               output_folder: str,
                               required_parts: List[str] = [],
                               auto_map_midi = True,
                               groove2groove_temperature:float = 0.4,
                               groove2groove_model: Groove2GrooveModelName = Groove2GrooveModelName.V01_DRUMS,
                               groove2groove_seed: int = 42,
                               replace_if_file_exist = True,
                               verbose=True, 
                               python_exe_for_grv2grv_env='/home/ubuntu/.conda/envs/groove2groove/bin/python'):

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
    :param groove2groove_seed: int, groove2groove random sampling seed (for obtaining different results). default=42
    :param replace_if_file_exist: Bool flag. If True and output file exists, replace it with the new version.
    :param verbose: Bool flag. If True, print more information to the terminal.
    :param python_exe_for_grv2grv_env: Path to the Python executable with matching environment for groove2groove.
    """
    create_blend_per_part(
        content_midi_path=midi_path, 
        content_structure_xls_path=structure_xls_path,
        style_midi_path=midi_path, 
        style_structure_xls_path=structure_xls_path,
        output_folder=output_folder,
        required_parts=required_parts,
        auto_map_midi=auto_map_midi,
        groove2groove_temperature=groove2groove_temperature,
        groove2groove_model=groove2groove_model,
        groove2groove_seed=groove2groove_seed,
        replace_if_file_exist=replace_if_file_exist,
        verbose=verbose, 
        python_exe_for_grv2grv_env=python_exe_for_grv2grv_env
    )



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
    parser.add_argument("--groove2groove_seed", type=int, default=42, 
                        help="Groove2groove model random seed to use.")
    parser.add_argument("--replace_if_file_exist", type=bool, default=True, 
                        help="Replace the file if it exists.")
    parser.add_argument("--verbose", type=bool, default=True, 
                        help="Print more information to the terminal.")
    parser.add_argument("--python_exe_for_grv2grv_env", type=str, default='/home/ubuntu/.conda/envs/groove2groove/bin/python', 
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
            groove2groove_seed=args.groove2groove_seed,
            replace_if_file_exist=args.replace_if_file_exist,
            verbose=args.verbose,
            python_exe_for_grv2grv_env=args.python_exe_for_grv2grv_env)

    else:
        # TODO: get rid of this - NATAN - Maybe add example files?
        print('NO arguments were given, using a default')
        midi_path = "data/HitCraft/Black Music Projects/Sub - Genre Afrobeat/57 Afrobeat #1 In F#m/Exports/57 Afrobeat #1 In F#m.midi" 
        structure_xls_path = "data/HitCraft/Black Music Projects/Sub - Genre Afrobeat/57 Afrobeat #1 In F#m/Exports/57 Afrobeat #1 In F#m St.xlsx" 
        output_folder = "/home/ubuntu/out_folder_test1"
        create_self_blend_per_part(midi_path=midi_path, structure_xls_path=structure_xls_path, 
                                output_folder=output_folder, verbose=True, replace_if_file_exist=True,
                                python_exe_for_grv2grv_env='/home/ubuntu/.conda/envs/groove2groove5/bin/python')