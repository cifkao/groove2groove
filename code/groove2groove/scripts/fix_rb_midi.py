#!/usr/bin/env python3
"""Fix a RealBand MIDI file."""

import argparse
import re
import sys

import mido


class MetaSpec_key_signature(mido.midifiles.meta.MetaSpec_key_signature):

    def decode(self, message, data):
        try:
            super().decode(message, data)
        except mido.midifiles.meta.KeySignatureError:
            message.key = None

    def check(self, name, value):
        if value is not None:
            super().check(name, value)


def main():
    # Prevent KeySignatureError on invalid key signature
    mido.midifiles.meta.add_meta_spec(MetaSpec_key_signature)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_file')
    parser.add_argument('output_file')
    parser.add_argument('--remove-re', type=str, action='append', default=[])
    parser.add_argument('--remove', type=str, action='append', default=[])
    parser.add_argument('--ignore-if-empty', action='store_true')
    args = parser.parse_args()

    midi_file = mido.MidiFile(args.input_file)

    num_invalid = 0
    for track in midi_file.tracks:
        # First, find which channels appear in the track
        channels = set()
        for message in track:
            if isinstance(message, mido.Message):
                channels.add(message.channel)
        channels = sorted(channels)

        messages = list(track)
        track.clear()
        for message in messages:
            # Detect and remove invalid messages
            if isinstance(message, mido.MetaMessage):
                if message.type == 'key_signature' and message.key is None:
                    num_invalid += 1
                    continue

            track.append(message)

            # Duplicate program changes into all channels in the track
            if message.type == 'program_change':
                track.extend(
                    mido.Message('program_change', program=message.program, channel=channel, time=0)
                    for channel in channels if channel != message.channel)

    if num_invalid:
        print(f'Removed {num_invalid} invalid messages', file=sys.stderr)

    # Remove tracks with the given name.
    for track in list(midi_file.tracks):
        if (any(re.search(regex, track.name) for regex in args.remove_re)
                or any(track.name == name for name in args.remove)):
            midi_file.tracks.remove(track)

    if args.ignore_if_empty:
        # If all tracks are empty (contain no notes), ignore the file
        if not any(msg.type in ['note_on', 'note_off']
                   for track in midi_file.tracks for msg in track):
            print(f'Ignoring empty file {args.input_file}', file=sys.stderr)
            return

    midi_file.save(args.output_file)


if __name__ == '__main__':
    main()
