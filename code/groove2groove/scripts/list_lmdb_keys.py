#!/usr/bin/env python3
"""Lists all keys in an LMDB database."""
import argparse
import contextlib

import lmdb
from note_seq.protobuf import music_pb2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('db_path', metavar='DB',
                        help='the database path')
    parser.add_argument('--skip-empty-sequences', action='store_true',
                        help='interpret the database values as NoteSequences and report only '
                             'non-empty ones')
    args = parser.parse_args()

    with contextlib.ExitStack() as ctx:
        db = ctx.enter_context(
            lmdb.open(args.db_path, subdir=False, readonly=True, lock=False))
        txn = ctx.enter_context(db.begin(buffers=True))

        for key, val in txn.cursor():
            if args.skip_empty_sequences:
                seq = music_pb2.NoteSequence.FromString(val)
                if not seq.notes:
                    continue

            print(bytes(key).decode())


if __name__ == '__main__':
    main()
