from typing import Dict, Tuple, List, Optional
import sys
from pathlib import Path
import argparse
from session_grv2grv_pipeline_utils import pre_process_midi_file_and_save, post_process_midi_file_and_save
from groove2groove_wrapper import run_groove2groove, Groove2GrooveModelName, run_groove2groove_evaluation_script

# run per-part blending of two MIDIs

def create_blend_per_part(content_midi_path: str, 
                          content_structure_xls_path: str,
                          style_midi_path: str, 
                          style_structure_xls_path: str,
                          output_folder: str,
                          required_parts: List[str] = [],
                          auto_map_midi = True,
                          groove2groove_temperature:float = 0.4,
                          groove2groove_model: Groove2GrooveModelName = Groove2GrooveModelName.V01_DRUMS,
                          groove2groove_seed: Optional[int] = None,
                          replace_if_file_exist = True,
                          verbose=True, 
                          python_exe_for_grv2grv_env='/home/ubuntu/.conda/envs/groove2groove/bin/python'):

    """Util function for creating a self-blend per part of a MIDI file using groove2groove.
    Self blend involves partition of the MIDI to parts (according to a given xls), splitting drums, 
    sequential midi mapping, running groove2groove for each part with itself, midi mapping back, adding the original drums,
    and possibly restoring the BPM value of the original part. Temporary files are saved under 'temp' subfolder of the output folder, 
    while the final self_blend output in a given output_folder.

    :param content_midi_path: Path to the input Content MIDI file.
    :param content_structure_xls_path: Path to the Excel file containing the Content MIDI parts' structure in Session42 format, 
                               which includes part valid name, start bar, and end bar.
    :param style_midi_path: Path to the input Style MIDI file.
    :param style_structure_xls_path: Path to the Excel file containing the Style MIDI parts' structure in Session42 format, 
                               which includes part valid name, start bar, and end bar.
    :param output_folder: Desired output folder for the self-blend outputs. Temporary files will be saved under 'temp' sub-folder.
    :param required_parts: List of strings specifying the required structure parts to be processed. 
                           If an empty list is given, use all the parts in the structure xls.
    :param auto_map_midi: Bool flag for enabling sequential MIDI program number mapping 
                          (used to overcome plug-in problems for MIDI files without program mapping).
    :param groove2groove_temperature: Float between 0-1, groove2groove model temperature parameter. Higher = more random output.
    :param groove2groove_model: Groove2GrooveModelName or string, specifying the groove2groove model to use (v01_drums_vel, v01_drums, etc.).
    :param groove2groove_seed: int, groove2groove random sampling seed (for obtaining different results).
    :param replace_if_file_exist: Bool flag. If True and output file exists, replace it with the new version.
    :param verbose: Bool flag. If True, print more information to the terminal.
    :param python_exe_for_grv2grv_env: Path to the Python executable with matching environment for groove2groove.
    """

    split_drums = True
    no_drum_part_name_extension = '_no_drum'
    drum_part_name_extension = '_only_drum'
    grv2grv_extension = (('D' if 'drum' in str(groove2groove_model) else '') + ('V' if 'vel' in str(groove2groove_model) else '') + 
                         '_T' + str(groove2groove_temperature).replace('.','')) 

    # for fixing bpm  
    replace_bpm = False
    # define preprocess output folder
    preprocess_out_folder = Path(output_folder) / 'temp'

   # run pre_processing + save files
   # TODO should I map the content? how about the drums? NATAN
    content_saved_path_list = pre_process_midi_file_and_save(content_midi_path, content_structure_xls_path, preprocess_out_folder, 
                                                        required_parts=required_parts,
                                                        auto_map_midi=auto_map_midi, split_drum = split_drums, 
                                                        replace_if_file_exist=replace_if_file_exist, verbose=verbose)
    # do not run pre-processing twice for self-blend
    if (content_midi_path == style_midi_path) and (content_structure_xls_path == style_structure_xls_path):
        style_saved_path_list = content_saved_path_list
        if verbose: 
            print('self bland, assuming identical content and style MIDIs')
    else:
        style_saved_path_list = pre_process_midi_file_and_save(style_midi_path, style_structure_xls_path, preprocess_out_folder, 
                                                                required_parts=required_parts,
                                                                auto_map_midi=auto_map_midi, split_drum = split_drums, 
                                                                replace_if_file_exist=replace_if_file_exist, verbose=verbose)


    style_bpm_path = [p for p in style_saved_path_list if p.endswith('.bpm.txt')][0]
    style_program_dict_path = [p for p in style_saved_path_list if p.endswith('.program_dict.json')][0]

    for content_midi_file_part_no_drum in content_saved_path_list:
        if content_midi_file_part_no_drum.endswith(f'{no_drum_part_name_extension}.mid'):
            # get matching style file:
            style_midi_file_part_no_drum = content_midi_file_part_no_drum.replace(Path(content_midi_path).stem, Path(style_midi_path).stem)
            if not Path(style_midi_file_part_no_drum).exists():
                if verbose:
                    print(f"Cannot find a match to Content {content_midi_file_part_no_drum}, Style {style_midi_file_part_no_drum} does not exist. skipping...")
                    continue
                    
            midi_grv2grv_out_path = Path(preprocess_out_folder) / f"{Path(content_midi_file_part_no_drum).stem}.X.{Path(style_midi_file_part_no_drum).stem}.{grv2grv_extension}.mid" 

            if replace_if_file_exist or not midi_grv2grv_out_path.exists():
            # run groove2groove with the files
                run_groove2groove(content_midi_file_part_no_drum, style_midi_file_part_no_drum, midi_grv2grv_out_path, model_name=groove2groove_model, 
                                temperature=groove2groove_temperature, python_exe_for_grv2grv_env=python_exe_for_grv2grv_env, verbose=verbose)
            elif verbose:
                print(f"groove2groove output {midi_grv2grv_out_path} exists, skipping groove2groove run...")   
            
            analysis_out_path = Path(preprocess_out_folder) / midi_grv2grv_out_path.stem.replace(grv2grv_extension, 'analysis.json')
            # run evaluation with the files
            if replace_if_file_exist or not analysis_out_path.exists():
                run_groove2groove_evaluation_script(content_midi_file_part_no_drum, style_midi_file_part_no_drum, midi_grv2grv_out_path, 
                                                    analysis_out_path = analysis_out_path,
                                                    model_name=groove2groove_model,  
                                                    temperature=groove2groove_temperature,
                                                    seed=groove2groove_seed, 
                                                    python_exe_for_grv2grv_env=python_exe_for_grv2grv_env, 
                                                    verbose=verbose)
            elif verbose:
                print(f"groove2groove evaluation file {analysis_out_path} exists, skipping groove2groove evaluation run...")  

            # run post processing. if we use original drums we take the content so the length would match.
            content_drum_midi_path = content_midi_file_part_no_drum.replace(f'{no_drum_part_name_extension}.mid',f'{drum_part_name_extension}.mid')
            
            # Create final output file name and path: 
            post_processing_output_midi_name = Path(midi_grv2grv_out_path).stem.replace(no_drum_part_name_extension,'')
            post_processing_output_midi_name += '_orig_drums_final.mid' if split_drums else '_final.mid'
            post_processing_output_midi_path = Path(output_folder) / post_processing_output_midi_name                            
            
            # run post processing
            post_process_midi_file_and_save(midi_grv2grv_out_path=midi_grv2grv_out_path, 
                                            post_processing_output_midi_path=post_processing_output_midi_path,
                                            automap_back=auto_map_midi,
                                            program_dict_path=style_program_dict_path,
                                            add_orig_drum=split_drums and Path(content_drum_midi_path).exists(),
                                            drum_midi_path=content_drum_midi_path,
                                            replace_bpm=replace_bpm,
                                            bpm_path=style_bpm_path,
                                            replace_if_file_exist=replace_if_file_exist,
                                            verbose=verbose)
    if verbose:
        print('Done!')


def parse_arguments():
    "Parser for the arguments of create_blend_per_part"
    parser = argparse.ArgumentParser(description="Create blend per part for given Content and Style MIDIs file using groove2groove.")
    parser.add_argument("content_midi_path", type=str, help="Path to the input Content MIDI file.")
    parser.add_argument("content_structure_xls_path", type=str, help="Path to the Excel file containing the Content MIDI parts' structure in Session42 format.")
    parser.add_argument("style_midi_path", type=str, help="Path to the input Style MIDI file.")
    parser.add_argument("style_structure_xls_path", type=str, help="Path to the Excel file containing the Style MIDI parts' structure in Session42 format.")    
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
    parser.add_argument("--groove2groove_seed", type=int, default=None, 
                        help="Groove2groove model random seed for sampling.")
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
        create_blend_per_part(
            content_midi_path=args.content_midi_path,
            content_structure_xls_path=args.content_structure_xls_path,
            style_midi_path=args.style_midi_path,
            style_structure_xls_path=args.style_structure_xls_path,
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
        content_midi_path = "data/HitCraft/Black Music Projects/Sub - Genre Afrobeat/57 Afrobeat #1 In F#m/Exports/57 Afrobeat #1 In F#m.midi" 
        content_structure_xls_path = "data/HitCraft/Black Music Projects/Sub - Genre Afrobeat/57 Afrobeat #1 In F#m/Exports/57 Afrobeat #1 In F#m St.xlsx" 
        style_midi_path = "data/HitCraft/Black Music Projects/Sub - Genre Reggae/18 Reggae 2 In Bm/Exports/18 Reggae 2 In Bm.midi"
        style_structure_xls_path = "data/HitCraft/Black Music Projects/Sub - Genre Reggae/18 Reggae 2 In Bm/Exports/18 Reggae 2 In Bm St.xlsx"

        output_folder = "/home/ubuntu/out_folder_test1"
        create_blend_per_part(content_midi_path=content_midi_path, content_structure_xls_path=content_structure_xls_path, 
                              style_midi_path=style_midi_path, style_structure_xls_path=style_structure_xls_path, 
                              output_folder=output_folder, verbose=True, replace_if_file_exist=True,
                              python_exe_for_grv2grv_env='/home/ubuntu/.conda/envs/groove2groove5/bin/python')