import abc
import csv
import collections
import contextlib
import gzip
import json
import logging
import random

import lmdb
from magenta.music.protobuf import music_pb2
from magenta.music import midi_io, sequences_lib
from museflow.io.note_sequence_io import save_sequences_db
from museflow.note_sequence_utils import normalize_tempo, split_on_downbeats
import numpy as np


_LOGGER = logging.getLogger(__name__)


class Loader(abc.ABC):

    @abc.abstractmethod
    def load(self):
        pass

    def __iter__(self):
        return self.load()


class TrainLoader(Loader):

    def __init__(self, metadata_path, db_path=None, source_db_path=None, target_db_path=None,
                 random_seed=None, reseed=False, allow_same_style=False, autoencode=False,
                 mode='one_shot_random'):
        self._source_db_path = source_db_path or db_path
        self._target_db_path = target_db_path

        with gzip.open(metadata_path, 'rt') as f:
            self._metadata = json.load(f)
        self._segment_index = _build_segment_index(self._metadata)
        self._style_index = _build_style_index(self._metadata)

        if random_seed is None:
            random_seed = random.random()
        self._random = random.Random(random_seed)
        self._random_seed = random_seed
        self._reseed = reseed

        self._autoencode = autoencode
        self._allow_same_style = allow_same_style or autoencode

        if mode not in ['one_shot_random', 'style_id']:
            raise ValueError(f"mode '{mode}' not recognized")
        self._mode = mode

    def load(self):
        if self._reseed:
            self._random.seed(self._random_seed)

        with contextlib.ExitStack() as ctx:
            src_db = ctx.enter_context(
                lmdb.open(self._source_db_path, subdir=False, readonly=True, lock=False))
            tgt_db = None
            if self._target_db_path:
                tgt_db = ctx.enter_context(
                    lmdb.open(self._target_db_path, subdir=False, readonly=True, lock=False))

            src_txn = ctx.enter_context(src_db.begin(buffers=True))
            tgt_txn = ctx.enter_context(tgt_db.begin(buffers=True)) if tgt_db else src_txn
            tgt_cur = tgt_txn.cursor()
            style_cur = tgt_txn.cursor()

            # Load the source segments sequentially. For each source segment, go through all
            # corresponding target segments. For each target segment, pick one of the corresponding
            # style segments at random.
            for src_key, src_val in src_txn.cursor():
                src_key = bytes(src_key).decode()
                src_seq = _deserialize_seq(src_val)

                for tgt_key, style_key in self._get_tgt_and_style_keys(src_key):
                    tgt_seq = _deserialize_seq(tgt_cur.get(tgt_key.encode()))
                    if self._mode == 'one_shot_random':
                        style = _deserialize_seq(style_cur.get(style_key.encode()))
                    elif self._mode == 'style_id':
                        style = style_key

                    yield src_seq, style, tgt_seq

    def _get_tgt_and_style_keys(self, src_key):
        if self._autoencode:
            if self._mode == 'one_shot_random':
                return [(src_key, src_key)]
            elif self._mode == 'style_id':
                return [(src_key, self._metadata[src_key]['style'])]

        result = []
        for tgt_key in self._segment_index[src_key]:
            if self._mode == 'one_shot_random':
                if (not self._allow_same_style and
                        self._metadata[tgt_key]['style'] == self._metadata[src_key]['style']):
                    continue

                style_key = self._random.choice(self._style_index[tgt_key])
            elif self._mode == 'style_id':
                style_key = self._metadata[tgt_key]['style']
            result.append((tgt_key, style_key))
        return result


class EvalPipeline(Loader):

    def __init__(self, source_db_path, key_pairs_path, style_db_path=None, skip_empty=True):
        # If style_db_path is None, run in style translation mode (passing style IDs instead
        # of style examples).

        self._source_db_path = source_db_path
        self._style_db_path = style_db_path
        self._key_pairs_path = key_pairs_path
        self._skip_empty = skip_empty

        self.key_pairs = None

    def load(self):
        self.key_pairs = []
        total_examples = 0
        empty_source_seqs = 0
        empty_style_seqs = 0

        with contextlib.ExitStack() as ctx:
            source_db = ctx.enter_context(
                lmdb.open(self._source_db_path, subdir=False, readonly=True, lock=False))
            if self._style_db_path:
                style_db = ctx.enter_context(
                    lmdb.open(self._style_db_path, subdir=False, readonly=True, lock=False))
            key_pairs_file = ctx.enter_context(open(self._key_pairs_path, 'r'))

            source_txn = ctx.enter_context(source_db.begin(buffers=True))
            if self._style_db_path:
                style_txn = ctx.enter_context(style_db.begin(buffers=True))

            for source_key, style_key in csv.reader(key_pairs_file, delimiter='\t'):
                total_examples += 1
                skip = False

                source_seq = _deserialize_seq(source_txn.get(source_key.encode()), allow_none=True)
                if source_seq is not None and not source_seq.notes:
                    empty_source_seqs += 1
                    skip = skip or self._skip_empty

                if self._style_db_path:
                    style_seq_or_id = _deserialize_seq(style_txn.get(style_key.encode()),
                                                       allow_none=True)
                    if style_seq_or_id is not None and not style_seq_or_id.notes:
                        empty_style_seqs += 1
                        skip = skip or self._skip_empty
                else:
                    style_seq_or_id = style_key

                if skip or source_seq is None or style_seq_or_id is None:
                    continue
                self.key_pairs.append((source_key, style_key))
                yield source_seq, style_seq_or_id, None

        _LOGGER.info(f'Loaded {len(self.key_pairs)} / {total_examples} examples.')
        _LOGGER.info(f'Found {empty_source_seqs} empty source sequences and '
                     f'{empty_style_seqs} empty style sequences.')

    def save(self, sequences, db_path):
        if self.key_pairs is None:
            raise RuntimeError("'save' called before 'load'")
        keys = ['{}_{}'.format(*kp) if kp else None for kp in self.key_pairs]
        save_sequences_db(sequences, keys, db_path)


class MidiPipeline(Loader):

    def __init__(self, source_path, style_path, bars_per_segment=None, warp=False):
        self._source_path = source_path
        self._style_path = style_path
        self._bars_per_segment = bars_per_segment
        self._warp = warp

        self.key_pairs = None
        self._durations = []
        self._target_tempo = None

    def load(self):
        self.key_pairs = []

        source_seq_full = midi_io.midi_file_to_note_sequence(self._source_path)
        style_seq = midi_io.midi_file_to_note_sequence(self._style_path)
        if self._warp:
            self._target_tempo = style_seq.tempos[0].qpm
            source_seq_full = normalize_tempo(source_seq_full, 60.)
            style_seq = normalize_tempo(style_seq, 60.)

        if self._bars_per_segment:
            source_segments = split_on_downbeats(source_seq_full, self._bars_per_segment)
        else:
            source_segments = [source_seq_full]
        assert len(source_segments) > 0

        boundaries = []
        for i, source_seq in enumerate(source_segments):
            self.key_pairs.append((str(i), None))
            boundaries.append(source_seq.subsequence_info.start_time_offset)
            yield source_seq, style_seq, None
        # source_seq is now the last source segment
        boundaries.append(source_seq.subsequence_info.end_time_offset)  # pylint: disable=undefined-loop-variable

        self._durations = np.diff(boundaries).tolist()

    def save(self, sequences, path):
        sequences = list(sequences)
        if len(sequences) != len(self._durations):
            raise RuntimeError(f'Expected {len(self._durations)} sequences, got {len(sequences)}')

        sequences = [sequences_lib.trim_note_sequence(seq, 0., dur)
                     for seq, dur in zip(sequences, self._durations)]
        sequence = sequences_lib.concatenate_sequences(sequences, self._durations)
        if self._warp:
            sequence, _ = sequences_lib.adjust_notesequence_times(
                sequence, lambda t: t * 60. / self._target_tempo)
            sequence.tempos.add().qpm = self._target_tempo
        midi_io.note_sequence_to_midi_file(sequence, path)


def _build_segment_index(metadata):
    """Return a dictionary mapping each key to a list of keys corresponding to the same segment."""
    segment_id_to_keys = collections.defaultdict(list)
    index = {}
    for key, item in metadata.items():
        full_segment_id = (item['song_name'], item['segment_id'])
        item['full_segment_id'] = full_segment_id
        segment_id_to_keys[full_segment_id].append(key)
        index[key] = segment_id_to_keys[full_segment_id]
    return index


def _build_style_index(metadata):
    """Return a dictionary mapping each key to a list of keys with the same style."""
    style_to_keys = collections.defaultdict(list)
    index = {}
    for key, item in metadata.items():
        style = item['style']
        style_to_keys[style].append(key)
        index[key] = style_to_keys[style]
    return index


def _deserialize_seq(string, allow_none=False):
    if string is None and allow_none:
        return None
    return music_pb2.NoteSequence.FromString(string)