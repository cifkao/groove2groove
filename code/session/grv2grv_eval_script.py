#!/usr/bin/env python3
import os
import scipy
from pathlib import Path
import argparse
import json

from note_seq import midi_io
from museflow.note_sequence_utils import filter_sequence 
from confugue import Configuration
from groove2groove.eval.style_profiles import extract_all_stats
from groove2groove.eval.notes_chroma_similarity import chroma_similarity
import numpy as np


COMPARE_ONLY_MATCHING = True
model_name_dict = {'N':'None', 'V':'Velocity', 'DV':'Drums and Velocity', 'D': 'Drums'}

STYLE_PROFILE_DIR = 'experiments/eval/style_profiles'
STYLE_PROFILE_CFG_PATH = os.path.join(STYLE_PROFILE_DIR, 'config.yaml')
STYLE_PROFILE_DRUMS_CFG_PATH = os.path.join(STYLE_PROFILE_DIR, 'config_drums.yaml')

with open(STYLE_PROFILE_CFG_PATH, 'rb') as f:
    STYLE_PROFILE_FN = Configuration.from_yaml(f).bind(extract_all_stats)
with open(STYLE_PROFILE_DRUMS_CFG_PATH, 'rb') as f:
    STYLE_PROFILE_DRUMS_FN = Configuration.from_yaml(f).bind(extract_all_stats)


def evaluate_content(sequence, reference):
    """Evaluate the content similarity of a sequence to a reference."""
    # Is filtering the sequence necessary?
    sequence = filter_sequence(sequence, drums=False, copy=True)
    reference = filter_sequence(reference, drums=False, copy=True)
    return {
        'content_score': chroma_similarity(sequence, reference,
                                     sampling_rate=12, window_size=24, stride=12, use_velocity=False)
    }


def cosine_similarity(hist1, hist2):
    with np.errstate(divide='ignore', over='warn', under='ignore', invalid='ignore'):
        return 1. - scipy.spatial.distance.cosine(hist1.reshape(1, -1), hist2.reshape(1, -1))

def filter_sequences(sequences, **kwargs):
    return [filter_sequence(seq, copy=True, **kwargs) for seq in sequences]


def evaluate_style(sequences, ref_stats=None, ref_sequences=None, is_drum=False, separate_drums=False):
    """Evaluate the style similarity of a set of sequences to a reference."""
    sequences = filter_sequences(sequences, drums=is_drum) #programs=[out_program]  # what about seperating each instrument? or each program=track?
    if ref_sequences is not None:
        ref_sequences = filter_sequences(ref_sequences, drums=is_drum)

    extract_fn = STYLE_PROFILE_FN if not is_drum else STYLE_PROFILE_DRUMS_FN
    stats = extract_fn(data=sequences)
    if ref_stats is None:
        ref_stats = extract_fn(data=ref_sequences)
    metrics = {name + ('_drums' if is_drum and separate_drums else ''):
                   cosine_similarity(stats[name], ref_stats[name])
               for name in stats if name in ref_stats}

    return metrics

def analyze_output(cont_midi_path, style_midi_path, out_midi_path,
                   model_name=None, temperature=None):
    results = {}
    results['output_file'] = Path(out_midi_path).name 
    results['content_file'] = Path(cont_midi_path).name
    results['style_file']  = Path(style_midi_path).name    
    if model_name is not None:
        results['model_name'] = model_name
    if temperature is not None:
        results['temperature'] = temperature

    cont_midi  = midi_io.midi_file_to_note_sequence(cont_midi_path)
    style_midi = midi_io.midi_file_to_note_sequence(style_midi_path)
    out_midi   = midi_io.midi_file_to_note_sequence(out_midi_path)
    results.update(evaluate_content(out_midi, cont_midi))

    # TODO: understand the drum thing! IMPORTANT

    style_metrics = evaluate_style(sequences=[out_midi], ref_sequences=[style_midi], is_drum = False)
    results.update(style_metrics)
    style_metrics = evaluate_style(sequences=[out_midi], ref_sequences=[style_midi], is_drum = True, separate_drums=True)
    results.update(style_metrics)
    
    # delete the following entities:
    for key_to_delete in ['time_pitch_diff_drums', 'onset.velocity_drums']:
        if key_to_delete in results:
            results.pop(key_to_delete)
    return results


def parse_args():
    """Get command line arguments for running groove2groove evaluation between style, contend and output MIDI files."""
    parser = argparse.ArgumentParser(description="Compare groove2groove output with content and style MIDIs using grv2grv metrics.")
    parser.add_argument('--cont_midi_path', type=str, required=True, help="Path to the content MIDI.")
    parser.add_argument('--style_midi_path', type=str, required=True, help="Path to the style MIDI.")
    parser.add_argument('--out_midi_path', type=str, required=True, help="Path to Groove2Groove output.")
    parser.add_argument('--analysis_out_path', type=str, default=None, help="analysis json output path. If not given - the extension .analysis.json will be added to the original groove2groove output filename.")
    parser.add_argument('--model_name', type=str, default=None, help="Name of the groove2groove model.")
    parser.add_argument('--temperature', type=float, default=None, help="Temperature value that was used to generate the groove2groove output MIDI.")
    parser.add_argument('--verbose', type=bool, default=True, help='Verbose output. Default is True.')
    return parser.parse_args()


if __name__=='__main__':
    args = parse_args()

    out_midi_path = Path(args.out_midi_path)
    file_analysis_json_path =  args.analysis_out_path if args.analysis_out_path is not None else out_midi_path.parent / (out_midi_path.stem + '.analysis.json')
    results = analyze_output(cont_midi_path=args.cont_midi_path, 
                            style_midi_path=args.style_midi_path, 
                            out_midi_path=args.out_midi_path,
                            model_name=args.model_name,
                            temperature=args.temperature)

    if args.verbose:
        print(f'Results: {results}')    
    # Save the dictionary to a JSON file
    with open(file_analysis_json_path, 'w') as json_file:
        json.dump(results, json_file, indent=4)
        if args.verbose:
            print(f'Evaluation results saved to {file_analysis_json_path}')

    


