import numpy as np
from note_seq import midi_io

_EPSILON = 1e-9


def extract_features(note_sequences, features):
    """Extract a set of features from the given note sequences.

    Args:
        note_sequences: an iterable of `NoteSequence` protos.
        features: a dictionary with feature objects as values.

    Returns:
        A dictionary mapping keys from `features` to lists of feature values.
    """
    results = {key: [] for key in features}
    for sequence in note_sequences:
        for key, feature in features.items():
            old_len = len(results[key])
            results[key].extend(feature.extract(sequence))
            if len(results[key]) - old_len != len(sequence.notes):
                raise RuntimeError(f'Feature {key} has {len(results[key]) - old_len} values for '
                                   f'note sequence of length {len(sequence.notes)}')

    assert len(set(len(x) for x in results.values())) <= 1

    return results


class Pitch:
    """The MIDI pitch of the note."""

    def extract(self, sequence):
        for note in sequence.notes:
            yield note.pitch

    def get_bins(self, min_value=0, max_value=127):
        return np.arange(min_value, max_value + 1) - 0.5


class Duration:
    """The duration of the note.

    It is assumed that the tempo is normalized (typically to 60 BPM) so that the duration is
    expressed in beats.
    """

    def extract(self, sequence):
        for note in sequence.notes:
            yield note.end_time - note.start_time

    def get_bins(self, bin_size=1/6, max_value=2):
        return np.arange(0., max_value + bin_size - _EPSILON, bin_size)


class Velocity:
    """The MIDI velocity of the note."""

    def extract(self, sequence):
        for note in sequence.notes:
            yield note.velocity

    def get_bins(self, num_bins=8):
        return np.arange(0, 127, 128 / num_bins) - 0.5


class OnsetPositionInBar:
    """The time of the note onset expressed in beats from the most recent downbeat.

    If `bar_duration` and, optionally, `beat_duration` (1 by default) is given, it will be assumed
    that the tempo and the time signature are constant. Otherwise, the downbeat times will be
    obtained using pretty_midi (note that this part has not been tested).
    """

    def __init__(self, bar_duration=None, beat_duration=None):
        self._bar_duration = bar_duration
        self._beat_duration = 1. if bar_duration and not beat_duration else beat_duration

    def extract(self, sequence):
        if self._bar_duration:
            for note in sequence.notes:
                yield (note.start_time % self._bar_duration) / self._beat_duration
        else:
            # Warning: Untested code ahead
            pm = midi_io.sequence_proto_to_pretty_midi(sequence)
            downbeat_ticks = [pm.time_to_tick(t) for t in pm.get_downbeats(sequence)]

            bar_idx = 0
            for note in sequence.notes:
                onset_tick = pm.time_to_tick(note.start_time)
                while bar_idx + 1 < len(downbeat_ticks) and downbeat_ticks[bar_idx] > onset_tick:
                    bar_idx += 1
                yield (onset_tick - downbeat_ticks[bar_idx]) / pm.resolution

    def get_bins(self, bin_size=1/6, max_beats=None):
        if max_beats is None:
            if self._bar_duration:
                max_beats = self._bar_duration / self._beat_duration
            else:
                raise ValueError('max_beats not specified while bar and beat duration is unknown')
        return np.arange(0., max_beats + bin_size - _EPSILON, bin_size)
