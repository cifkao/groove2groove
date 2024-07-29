# This is an example script for running session_grv2grv_self_blend_pipeline

path_to_content_midi_file='data/HitCraft_Examples/Black Music Projects/Sub - Genre Afrobeat/57 Afrobeat #1 In F#m/Exports/57 Afrobeat #1 In F#m.midi'
path_to_content_structure_xls='data/HitCraft_Examples/Black Music Projects/Sub - Genre Afrobeat/57 Afrobeat #1 In F#m/Exports/57 Afrobeat #1 In F#m St.xlsx'
path_to_style_midi_file='data/HitCraft_Examples/Black Music Projects/Sub - Genre Reggae/18 Reggae 2 In Bm/Exports/18 Reggae 2 In Bm.midi'
path_to_style_structure_xls='data/HitCraft_Examples/Black Music Projects/Sub - Genre Reggae/18 Reggae 2 In Bm/Exports/18 Reggae 2 In Bm St.xlsx'
output_folder='/home/ubuntu/out_folder_test_full_pipeline'
python_exe_for_grv2grv_env='/home/ubuntu/.conda/envs/groove2groove5/bin/python'

echo "running example: code/session/session_grv2grv_full_pipeline.py"

mkdir -p $output_folder 
python code/session/session_grv2grv_full_pipeline.py "$path_to_content_midi_file" "$path_to_content_structure_xls" \
"$path_to_style_midi_file" "$path_to_style_structure_xls" "$output_folder" \
--required_parts Verse Chorus --auto_map_midi True \
--groove2groove_temperature 0.4 --groove2groove_model v01_drums --groove2groove_seed 33  \
--replace_if_file_exist True --verbose True \
--python_exe_for_grv2grv_env "$python_exe_for_grv2grv_env"