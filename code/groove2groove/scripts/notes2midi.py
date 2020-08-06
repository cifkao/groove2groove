#!/usr/bin/env python2
"""Turn sequences of notes into MIDI files."""

import argparse
import collections
import gzip
import json
import logging
import os

import coloredlogs
import lmdb
from note_seq import midi_io, sequences_lib
from note_seq.protobuf import music_pb2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_file', metavar='FILE')
    parser.add_argument('output_dir', metavar='OUTPUTDIR')
    parser.add_argument('--stretch', type=str, metavar='RATIO')
    parser.add_argument('--metadata', type=str, metavar='FILE')
    parser.add_argument('--group-by-name', action='store_true')
    parser.add_argument('--duration', type=float)
    parser.add_argument('--trim', action='store_true')
    args = parser.parse_args()

    if args.stretch:
        # Calculate the time stretch ratio
        if ':' in args.stretch:
            a, b = args.stretch.split(':')
            stretch_ratio = float(a) / float(b)
        else:
            stretch_ratio = float(args.stretch)

    metadata = None
    if args.metadata:
        with gzip.open(args.metadata, 'rt') as f:
            metadata = json.load(f)

    if args.group_by_name:
        if not metadata:
            raise ValueError('--group-by-name requires --metadata')

        name_to_sequences = collections.defaultdict(list)

    os.makedirs(args.output_dir, exist_ok=True)

    with lmdb.open(args.input_file, subdir=False, readonly=True, lock=False) as db:
        with db.begin(buffers=True) as txn:
            for key, val in txn.cursor():
                key = bytes(key).decode()
                sequence = music_pb2.NoteSequence.FromString(val)

                if not sequence.tempos:
                    sequence.tempos.add().qpm = 60.

                if args.stretch:
                    sequence, _ = sequences_lib.adjust_notesequence_times(
                        sequence, lambda t: t * stretch_ratio)

                if args.trim:
                    if args.duration is None:
                        raise ValueError('--trim requires --duration')
                    sequence = sequences_lib.trim_note_sequence(sequence, 0., args.duration)

                if args.group_by_name:
                    if '_' in key:
                        src_key, style_key = key.split('_')
                        name, _ = os.path.splitext(metadata[src_key]['filename'])
                        style_name, _ = os.path.splitext(metadata[style_key]['filename'])
                        name = f'{name}__{style_name}'
                    else:
                        name, _ = os.path.splitext(key + '_' + metadata[key]['filename'])
                    name_to_sequences[name].append(sequence)
                else:
                    out_path = os.path.join(args.output_dir, key + '.mid')
                    midi_io.note_sequence_to_midi_file(sequence, out_path)

    if args.group_by_name:
        for name, sequences in name_to_sequences.items():
            sequence_durations = None
            if args.duration is not None:
                sequence_durations = [args.duration for _ in sequences]
            sequence = sequences_lib.concatenate_sequences(sequences, sequence_durations)

            out_path = os.path.join(args.output_dir, name + '.mid')
            midi_io.note_sequence_to_midi_file(sequence, out_path)


if __name__ == '__main__':
    coloredlogs.install(level='DEBUG', logger=logging.root, isatty=True)
    logging.getLogger('tensorflow').handlers.clear()
    main()
