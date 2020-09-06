#!/usr/bin/env python3
"""Fix key signatures in a MIDI file to make it possible to load it with mido."""

import argparse
import sys

import mido


class MetaSpec_key_signature(mido.midifiles.meta.MetaSpec_key_signature):

    def decode(self, message, data):
        data[1] &= 1
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
    args = parser.parse_args()

    midi_file = mido.MidiFile(args.input_file)

    for track in midi_file.tracks:
        invalid_messages = set()
        for message in list(track):
            # Detect invalid messages
            if isinstance(message, mido.MetaMessage):
                if message.type == 'key_signature' and message.key is None:
                    invalid_messages.add(id(message))

        # Remove invalid messages
        original_len = len(track)
        track[:] = (msg for msg in track if id(msg) not in invalid_messages)
        if len(track) != original_len:
            print('Removed {} invalid messages'.format(original_len - len(track)), file=sys.stderr)

    midi_file.save(args.output_file)


if __name__ == '__main__':
    main()
