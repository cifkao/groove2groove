#!/usr/bin/env python3
"""Convert a TFRecord file to an LMDB database."""
import argparse
import os
import random

import lmdb
import tensorflow as tf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_files', nargs='+', metavar='INPUT-FILE')
    parser.add_argument('output_file', metavar='OUTPUT-FILE')
    parser.add_argument('--shuffle', action='store_true')
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args()

    tf.enable_eager_execution()

    dataset = tf.data.TFRecordDataset(args.input_files)

    max_db_size = sum(os.path.getsize(path) for path in args.input_files) * 2
    num_records = sum(1 for _ in dataset)
    key_len = len(str(num_records - 1))
    keys = [str(i).zfill(key_len).encode() for i in range(num_records)]
    if args.shuffle:
        random.seed(args.seed)
        random.shuffle(keys)
    with lmdb.open(args.output_file, map_size=max_db_size, subdir=False) as db:
        with db.begin(write=True) as txn:
            for key, record in zip(keys, dataset):
                txn.put(key, record.numpy())


if __name__ == '__main__':
    main()
