#!/usr/bin/env python3
"""Splits MIDI files into segments and saves them as NoteSequence protobuffers.

Creates a TFRecord file named {OUTPUT_PREFIX}.tfrecord, containing the protobuffers, and a metadata
file named {OUTPUT_PREFIX}_meta.json.gz.
"""
import argparse
import gzip
import json
import os
import sys

import pretty_midi
from museflow import note_sequence_utils
from note_seq import midi_io
from note_seq.protobuf import music_pb2

try:
    from tensorflow.io import TFRecordWriter
except ImportError:
    from tensorflow.python_io import TFRecordWriter

BEAT = music_pb2.NoteSequence.TextAnnotation.BEAT
DOWNBEAT = '_DOWNBEAT'


def merge_equivalent_instruments(sequence, by_name=True, by_program=True):
    id_to_name = {}
    for info in sequence.instrument_infos:
        if info.instrument in id_to_name:
            raise ValueError(f'Instrument ID {info.instrument} is not unique')
        id_to_name[info.instrument] = info.name

    # Map events to keys, which define equivalence classes of instruments.
    # By default, the key is a tuple (name, program, is_drum).
    def get_key(event):
        # Careful, some events have invalid instrument IDs (not present in id_to_name).
        name = (id_to_name.get(event.instrument, event.instrument),) if by_name else ()
        program = (event.program,) if by_program else ()
        return name + program + (event.is_drum,)

    # Find the lowest instrument ID for each equivalence class.
    key_to_id = {}
    for collection in [sequence.notes, sequence.pitch_bends, sequence.control_changes]:
        for event in collection:
            key = get_key(event)
            if key not in key_to_id or key_to_id[key] > event.instrument:
                key_to_id[key] = event.instrument

    # Assign the new (disambiguated) instrument IDs.
    for collection in [sequence.notes, sequence.pitch_bends, sequence.control_changes]:
        for event in collection:
            event.instrument = key_to_id[get_key(event)]

    # Remove the redundant instrument infos.
    new_infos = [info for info in sequence.instrument_infos
                 if info.instrument in key_to_id.values()]
    del sequence.instrument_infos[:]
    sequence.instrument_infos.extend(new_infos)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input_dir', metavar='INPUT-DIR')
    parser.add_argument('output_prefix', metavar='OUTPUT-PREFIX')

    parser.add_argument('-b', '--bars-per-segment', type=lambda l: [int(x) for x in l.split(',')],
                        default=[8], metavar='NUM',
                        help='the number of bars per segment (default: 8)')
    parser.add_argument('-n', '--min-notes-per-segment', type=int, default=1, metavar='NUM',
                        help='discard segments with less than the given number of notes '
                             '(default: 1)')
    parser.add_argument('-t', '--force-tempo', type=float, default=None, metavar='BPM',
                        help='warp the sequences to match the given tempo')
    parser.add_argument('--skip-bars', type=int, default=0, metavar='NUM',
                        help='skip the given number of bars at the beginning')
    parser.add_argument('--merge-instruments', action='store_true',
                        help='causes equivalent instruments to be merged')

    args = parser.parse_args()

    # Collect all paths
    paths = []
    for dir_path, dirnames, filenames in os.walk(args.input_dir):
        dirnames.sort()
        filenames.sort()
        for fname in filenames:
            paths.append(os.path.join(dir_path, fname))

    metadata = []
    with TFRecordWriter(args.output_prefix + '.tfrecord') as writer:
        for path in paths:
            rel_path = os.path.relpath(path, args.input_dir)
            print(rel_path, file=sys.stderr, flush=True)
            midi = pretty_midi.PrettyMIDI(path)
            sequence = midi_io.midi_to_note_sequence(midi)
            sequence.filename = rel_path

            # Record the downbeat times so that they get updated by normalize_tempo later
            for time in midi.get_downbeats():
                annotation = sequence.text_annotations.add()
                annotation.time = time
                annotation.annotation_type = BEAT
                annotation.text = DOWNBEAT

            if args.merge_instruments:
                merge_equivalent_instruments(sequence)

            if args.force_tempo:
                sequence = note_sequence_utils.normalize_tempo(sequence, args.force_tempo)

            # Get the updated downbeats
            downbeats = [a.time for a in sequence.text_annotations
                         if (a.annotation_type, a.text) == (BEAT, DOWNBEAT)]
            del sequence.text_annotations[-len(downbeats):]

            for start, end, segment in note_sequence_utils.split_on_downbeats(
                    sequence, downbeats=downbeats,
                    bars_per_segment=args.bars_per_segment, skip_bars=args.skip_bars,
                    min_notes_per_segment=args.min_notes_per_segment, include_span=True):
                writer.write(segment.SerializeToString())
                metadata.append({
                    'filename': rel_path,
                    'segment_id': f'bar_{start}-{end}'
                })

    with gzip.open(args.output_prefix + '_meta.json.gz', 'wt', encoding='utf-8') as f:
        json.dump(metadata, f, separators=(',', ':'))


if __name__ == '__main__':
    main()
