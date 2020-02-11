#!/usr/bin/env python
import argparse
import gzip
import json
import random

from groove2groove.io import _build_segment_index, _build_style_index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('metadata_path')
    parser.add_argument('--max-per-src', type=int, default=1)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    with gzip.open(args.metadata_path, 'rt') as f:
        metadata = json.load(f)

    style_index = _build_style_index(metadata)
    segment_index = _build_segment_index(metadata)

    random.seed(args.seed)
    for src_key in sorted(metadata.keys()):
        count = 0

        tgt_keys = segment_index[src_key]
        random.shuffle(tgt_keys)
        for tgt_key in tgt_keys:
            if metadata[src_key]['style'] == metadata[tgt_key]['style']:
                continue

            style_keys = list(style_index[tgt_key])
            random.shuffle(style_keys)
            for style_key in style_keys:
                if count >= args.max_per_src:
                    break
                if tgt_key == style_key:
                    continue

                print(src_key, style_key, tgt_key, sep='\t')
                count += 1


if __name__ == '__main__':
    main()
