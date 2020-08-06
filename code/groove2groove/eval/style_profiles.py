#!/usr/bin/env python3
import argparse
import collections
import gzip
import json
import logging
import random
import sys

import coloredlogs
import lmdb
import numpy as np
from confugue import Configuration, configurable
from museflow import note_sequence_utils
from note_seq.protobuf.music_pb2 import NoteSequence

from groove2groove.eval import note_features

_LOGGER = logging.getLogger(__name__)


def time_pitch_diff_hist(data, max_time=2, bin_size=1/6, pitch_range=20, normed=True,
                         allow_empty=True):
    """Compute an onset-time-difference vs. interval histogram.

    Args:
        data: A list of Magenta `NoteSequence`s.
        max_time: The maximum time between two notes to be considered.
        bin_size: The bin size along the time axis.
        pitch_range: The number of pitch difference bins in each direction (positive or negative,
            excluding 0). Each bin has size 1.
        normed: Whether to normalize the histogram.
        allow_empty: If `True`, a histogram will be computed even if there are no notes in the
            input. Otherwise, `None` will be returned in such a case.

    Returns:
        A 2D `np.array` of shape `[max_time / bin_size, 2 * pitch_range + 1]`, or `None` if
        `data` is empty.
    """
    epsilon = 1e-9
    time_diffs, intervals = [], []
    for seq in data:
        onsets = [n.start_time for n in seq.notes]
        diff_mat = np.subtract.outer(onsets, onsets)

        # Count only positive time differences.
        index_pairs = zip(*np.where((diff_mat < max_time - epsilon) & (diff_mat >= 0.)))
        for j, i in index_pairs:
            if j == i:
                continue

            time_diffs.append(diff_mat[j, i])
            intervals.append(seq.notes[j].pitch - seq.notes[i].pitch)

    if not time_diffs and not allow_empty:
        return None

    with np.errstate(divide='ignore', invalid='ignore'):
        histogram, _, _ = np.histogram2d(
            intervals, time_diffs, normed=normed,
            bins=[np.arange(-(pitch_range + 1), pitch_range + 1) + 0.5,
                  np.arange(0., max_time + bin_size - epsilon, bin_size)])
    np.nan_to_num(histogram, copy=False)

    return histogram


NOTE_FEATURE_DEFS = {
    'duration': (note_features.Duration, {}),
    'onset': (note_features.OnsetPositionInBar, {'bar_duration': 4.}),
    'velocity': (note_features.Velocity, {}),
    'pitch': (note_features.Pitch, {})
}


NOTE_STAT_DEFS = [
    {
        'name': stat_name,
        'features': [{'name': feat_name} for feat_name in stat_name.split('.')],
    }
    for stat_name in ['onset', 'onset.duration', 'onset.velocity', 'pitch', 'onset.pitch']
]


@configurable
def extract_note_stats(data, *, _cfg):
    features = {key: _cfg['features'][key].configure(feat_type, **kwargs)
                for key, (feat_type, kwargs) in NOTE_FEATURE_DEFS.items()}
    feature_values = note_features.extract_features(data, features)

    @configurable
    def make_hist(name, normed=True, *, _cfg):
        feature_names = [f['name'] for f in _cfg.get('features')]
        with np.errstate(divide='ignore', invalid='ignore'):
            hist, _ = np.histogramdd(
                sample=[feature_values[name] for name in feature_names],
                bins=[_cfg['features'][i]['bins'].configure(features[name].get_bins)
                      for i, name in enumerate(feature_names)],
                normed=normed)
        np.nan_to_num(hist, copy=False)

        return name, hist

    # Create a dictionary mapping stat names to their values
    stats_cfg = _cfg['stats'] if 'stats' in _cfg else Configuration(NOTE_STAT_DEFS)
    return dict(stats_cfg.configure_list(make_hist))


@configurable
def extract_all_stats(data, *, _cfg):
    results = {}
    results['time_pitch_diff'] = _cfg['time_pitch_diff'].configure(
        time_pitch_diff_hist,
        data=data,
        normed=True,
        allow_empty=False)
    results.update(_cfg['note_stats'].configure(extract_note_stats, data=data))

    return {k: v for k, v in results.items() if v is not None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('db_path', metavar='DB-FILE')
    parser.add_argument('meta_path', metavar='METADATA-FILE')
    parser.add_argument('--config', metavar='YAML-FILE', default=None)
    parser.add_argument('--max-segments-per-style', type=int, default=None)
    parser.add_argument('--style-key', type=str, default='style')
    args = parser.parse_args()

    if args.config:
        with open(args.config, 'rb') as f:
            _cfg = Configuration.from_yaml(f)
    else:
        _cfg = Configuration({})

    random.seed(42)

    with gzip.open(args.meta_path, 'rt') as f:
        metadata = json.load(f)
    styles = sorted(set(v[args.style_key] for v in metadata.values()))
    keys_by_style = {s: [k for k in sorted(metadata.keys()) if metadata[k][args.style_key] == s]
                     for s in styles}

    def get_sequences(style):
        keys = list(keys_by_style[style])
        random.shuffle(keys)
        keys = keys[:args.max_segments_per_style]
        _LOGGER.info(f'Processing style {style} ({len(keys)} segments)...')
        with lmdb.open(args.db_path, subdir=False, readonly=True, lock=False) as db:
            with db.begin(buffers=True) as txn:
                for key in keys:
                    val = txn.get(key.encode())
                    seq = NoteSequence.FromString(val)
                    yield note_sequence_utils.normalize_tempo(seq)

    results = collections.defaultdict(dict)
    for style in styles:
        sequences = list(get_sequences(style))

        total_notes = sum(len(seq.notes) for seq in sequences)
        if total_notes < 2:
            _LOGGER.info(f'Skipping style {style} with {total_notes} note(s).')
            continue

        stats = _cfg.configure(extract_all_stats, data=sequences)
        for stat_name, stat in stats.items():
            results[stat_name][style] = stat

    json.dump(dict(results), sys.stdout, default=lambda a: a.tolist(), separators=(',', ':'))
    sys.stdout.write('\n')


if __name__ == '__main__':
    coloredlogs.install(level='INFO', logger=logging.root, isatty=True)
    main()
