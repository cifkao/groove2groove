#!/usr/bin/env python3
"""Permute a JSON dictionary according to the given key map.

The input and/or output file may be gzip-compressed.
"""
import argparse
import gzip
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('src_json_path', metavar='INPUT-FILE',
                        help='the input JSON file path')
    parser.add_argument('tgt_json_path', metavar='OUTPUT-FILE',
                        help='the output JSON file path')
    parser.add_argument('key_map_path', metavar='KEY-MAP',
                        help='a TSV file containing on each line a source key and a target key')
    args = parser.parse_args()

    if os.path.splitext(args.src_json_path)[1] == '.gz':
        with gzip.open(args.src_json_path, 'rt') as f:
            src_dict = json.load(f)
    else:
        with open(args.src_json_path) as f:
            src_dict = json.load(f)

    total = 0
    missing = 0
    tgt_dict = {}
    with open(args.key_map_path) as key_map_file:
        for line in key_map_file:
            src_key, tgt_key = line.rstrip('\n').split('\t')
            if src_key not in src_dict:
                missing += 1
                continue
            if tgt_key in tgt_dict:
                raise RuntimeError('Duplicate key')
            tgt_dict[tgt_key] = src_dict[src_key]
            total += 1

    if os.path.splitext(args.tgt_json_path)[1] == '.gz':
        with gzip.open(args.tgt_json_path, 'wt') as f:
            json.dump(tgt_dict, f)
    else:
        with open(args.tgt_json_path, 'w') as f:
            json.dump(tgt_dict, f)

    print('Wrote {} / {} entries; {} keys missing'.format(
        total, len(src_dict), missing), file=sys.stderr)


if __name__ == '__main__':
    main()
