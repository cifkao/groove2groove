#!/usr/bin/env python3
"""Permute an LMDB database according to the given key map."""
import argparse
import contextlib
import sys

import lmdb


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('src_db_path', metavar='INPUT-DB',
                        help='the input database path')
    parser.add_argument('tgt_db_path', metavar='OUTPUT-DB',
                        help='the output database path')
    parser.add_argument('key_map_path', metavar='KEY-MAP',
                        help='a TSV file containing on each line a source key and a target key')
    args = parser.parse_args()

    with contextlib.ExitStack() as ctx:
        key_map_file = ctx.enter_context(open(args.key_map_path))
        src_db = ctx.enter_context(
            lmdb.open(args.src_db_path, subdir=False, readonly=True, lock=False))
        tgt_db = ctx.enter_context(
            lmdb.open(args.tgt_db_path, subdir=False, readonly=False, lock=False,
                      map_size=2 * src_db.info()['map_size']))
        src_txn = ctx.enter_context(src_db.begin(buffers=True))
        tgt_txn = ctx.enter_context(tgt_db.begin(buffers=True, write=True))

        total = 0
        missing = 0
        for line in key_map_file:
            src_key, tgt_key = line.rstrip('\n').split('\t')
            val = src_txn.get(src_key.encode())
            if val is None:
                missing += 1
                continue
            if not tgt_txn.put(tgt_key.encode(), val, overwrite=False):
                raise RuntimeError('Duplicate key')
            total += 1

        print('Wrote {} / {} entries; {} keys missing'.format(
            total, src_db.stat()['entries'], missing), file=sys.stderr)


if __name__ == '__main__':
    main()
