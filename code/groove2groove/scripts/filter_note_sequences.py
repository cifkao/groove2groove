#!/usr/bin/env python3
"""Filters the notes in a TFRecord file of NoteSequences to meet a given set of criteria."""
import argparse
import re

import tensorflow as tf
from museflow.note_sequence_utils import filter_sequence
from note_seq.protobuf import music_pb2

try:
    from tensorflow.io import TFRecordWriter
except ImportError:
    from tensorflow.python_io import TFRecordWriter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_files', nargs='+', metavar='INPUT-FILE')
    parser.add_argument('output_file', metavar='OUTPUT-FILE')
    parser.add_argument('-i', '--instrument-re', type=re.compile, default=re.compile('.*'),
                        metavar='REGEX', help='a regular expression matching the instrument name')
    parser.add_argument('--instrument-id', type=lambda l: [int(x) for x in l.split(',')],
                        default=None, metavar='ID', help='the integer ID(s) of the instrument(s)')
    parser.add_argument('-p', '--program', type=lambda l: [int(x) for x in l.split(',')],
                        default=None, metavar='PRG', help='the MIDI program number(s)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--drums', action='store_true', help='include only drums')
    group.add_argument('--no-drums', action='store_false', dest='drums', help='exclude drums')
    group.set_defaults(drums=None)
    args = parser.parse_args()

    tf.enable_eager_execution()

    with TFRecordWriter(args.output_file) as writer:
        for record in tf.data.TFRecordDataset(args.input_files):
            sequence = music_pb2.NoteSequence.FromString(record.numpy())
            filter_sequence(sequence,
                            instrument_re=args.instrument_re,
                            instrument_ids=args.instrument_id,
                            programs=args.program,
                            drums=args.drums)
            writer.write(sequence.SerializeToString())


if __name__ == '__main__':
    main()
