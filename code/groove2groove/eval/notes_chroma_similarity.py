"""Measure chroma vector similarity ("content preservation").

Adapted from "Transferring The Style of Homophonic Music Using Recurrent Neural Networks and
Autoregressive Models", Wei-Tsung Lu and Li Su, ISMIR 2018.
http://ismir2018.ircam.fr/doc/pdfs/107_Paper.pdf
"""

import numpy as np
import pretty_midi
import scipy.signal
import scipy.spatial.distance
from note_seq import midi_io
from note_seq.protobuf.music_pb2 import NoteSequence


def chroma_similarity(sequence_a, sequence_b, sampling_rate, window_size, stride,
                      use_velocity=False):
    notes_a, notes_b = (_as_note_list(seq) for seq in (sequence_a, sequence_b))

    if not use_velocity:
        notes_a, notes_b = (_strip_velocity(notes) for notes in (notes_a, notes_b))

    chroma_a, chroma_b = (_get_chroma(notes, sampling_rate) for notes in (notes_a, notes_b))

    # Make sure the chroma matrices have the same dimensions.
    if chroma_a.shape[1] < chroma_b.shape[1]:
        chroma_a, chroma_b = chroma_b, chroma_a
    chroma_b = np.pad(chroma_b, [(0, 0), (0, chroma_a.shape[1] - chroma_b.shape[1])],
                      mode='constant')

    # Compute a moving average over time.
    avg_filter = np.ones((1, window_size)) / window_size
    chroma_avg_a, chroma_avg_b = (_convolve_strided(chroma, avg_filter, stride)
                                  for chroma in (chroma_a, chroma_b))

    return _average_cos_similarity(chroma_avg_a, chroma_avg_b)


def _as_note_list(sequence):
    if isinstance(sequence, NoteSequence):
        sequence = midi_io.note_sequence_to_pretty_midi(sequence)

    if isinstance(sequence, pretty_midi.PrettyMIDI):
        sequence = [note for instrument in sequence.instruments for note in instrument.notes]

    return sequence


def _strip_velocity(notes):
    return [pretty_midi.Note(pitch=n.pitch, start=n.start, end=n.end, velocity=127)
            for n in notes]


def _get_chroma(notes, sampling_rate):
    midi = pretty_midi.Instrument(0)
    midi.notes[:] = notes
    return midi.get_chroma(fs=sampling_rate)


def _average_cos_similarity(chroma_a, chroma_b):
    """Compute the column-wise cosine similarity, averaged over all non-zero columns."""
    nonzero_cols_ab = []
    for chroma in (chroma_a, chroma_b):
        col_norms = np.linalg.norm(chroma, axis=0)
        nonzero_cols = col_norms > 1e-9
        nonzero_cols_ab.append(nonzero_cols)
        # Note: 'np.divide' needs the 'out' parameter, otherwise the output would get written to
        # an uninitialized array.
        np.divide(chroma, col_norms, where=nonzero_cols, out=chroma)

    # Count the columns where at least one of the two matrices is nonzero.
    num_nonzero_cols = np.logical_or(*nonzero_cols_ab).sum()  # pylint: disable=no-value-for-parameter

    # Compute the dot product.
    return np.tensordot(chroma_a, chroma_b) / num_nonzero_cols


def _convolve_strided(data, filtr, stride):
    """Compute a 2D convolution with the given stride along the second dimension.

    A full (zero-padded) 2D convolution is computed, then subsampled according to the stride with
    an offset calculated so that the convolution window is aligned to the left edge of the original
    array.
    """
    convolution = scipy.signal.convolve2d(data, filtr, mode='full')
    offset = (filtr.shape[-1] - 1) % stride  # Make sure the windows are aligned
    return convolution[:, offset::stride]
