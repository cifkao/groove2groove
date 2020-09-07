#!/usr/bin/env python3
"""Given a list of MIDI files, filter them to include only those in 4/4 time."""

import sys

import pretty_midi


def main():
    files = sys.argv[1:]

    for fname in files:
        midi = pretty_midi.PrettyMIDI(fname)
        if len(midi.time_signature_changes) != 1:
            continue
        ts = midi.time_signature_changes[0]
        if ts.numerator == 4 and ts.denominator == 4:
            print(fname, flush=True)


if __name__ == '__main__':
    main()
