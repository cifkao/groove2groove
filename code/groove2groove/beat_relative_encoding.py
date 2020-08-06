import heapq
import logging
import warnings
from collections import defaultdict

import numpy as np
from museflow import note_sequence_utils
from museflow.encodings.performance_encoding import _compress_note_offs
from museflow.vocabulary import Vocabulary
from note_seq.constants import STANDARD_PPQ
from note_seq.protobuf import music_pb2

_LOGGER = logging.getLogger(__name__)


class BeatRelativeEncoding:

    def __init__(self, units_per_beat=12, velocity_unit=4, use_velocity=True, default_velocity=127,
                 use_all_off_event=False, use_drum_events=False, errors='remove',
                 warn_on_errors=False):

        self._units_per_beat = units_per_beat
        self._velocity_unit = velocity_unit
        self._use_velocity = use_velocity
        self._use_all_off_event = use_all_off_event
        self._use_drum_events = use_drum_events
        self._errors = errors
        self._warn_on_errors = warn_on_errors

        wordlist = (['<pad>', '<s>', '</s>'] +
                    [('NoteOn', i) for i in range(128)] +
                    [('NoteOff', i) for i in range(128)] +
                    ([('NoteOff', '*')] if use_all_off_event else []) +
                    ([('DrumOn', i) for i in range(128)] +
                     [('DrumOff', i) for i in range(128)]
                     if use_drum_events else []) +
                    [('SetTime', i) for i in range(units_per_beat)] +
                    [('SetTimeNext', i) for i in range(units_per_beat)])

        if use_velocity:
            max_velocity_units = (128 + velocity_unit - 1) // velocity_unit
            wordlist.extend([('SetVelocity', i + 1) for i in range(max_velocity_units)])
        self._default_velocity = default_velocity

        self.vocabulary = Vocabulary(wordlist)

    def encode(self, sequence, as_ids=True, add_start=False, add_end=False):
        sequence = note_sequence_utils.normalize_tempo(sequence)

        queue = _NoteEventQueue(sequence, quantization_step=1 / self._units_per_beat)
        events = [self.vocabulary.start_token] if add_start else []

        last_beat = 0
        last_t = 0
        velocity_quantized = None
        for t, note, is_onset in queue:
            if t > last_t:
                beat = t // self._units_per_beat
                step_in_beat = t % self._units_per_beat

                while beat - last_beat > 1:
                    # Skip to the beginning of the next beat
                    events.append(('SetTimeNext', 0))
                    last_beat += 1

                if beat == last_beat:
                    events.append(('SetTime', step_in_beat))
                else:  # beat == last_beat + 1
                    events.append(('SetTimeNext', step_in_beat))
                    last_beat += 1
                assert beat == last_beat

                last_t = t

            if is_onset:
                note_velocity = note.velocity
                if note_velocity > 127 or note_velocity < 1:
                    warnings.warn(f'Invalid velocity value: {note_velocity}')
                    note_velocity = self._default_velocity
                note_velocity_quantized = note_velocity // self._velocity_unit + 1
                if velocity_quantized != note_velocity_quantized:
                    velocity_quantized = note_velocity_quantized
                    if self._use_velocity:
                        events.append(('SetVelocity', velocity_quantized))

                if note.is_drum and self._use_drum_events:
                    events.append(('DrumOn', note.pitch))
                else:
                    events.append(('NoteOn', note.pitch))
            else:
                if note.is_drum and self._use_drum_events:
                    events.append(('DrumOff', note.pitch))
                else:
                    events.append(('NoteOff', note.pitch))

        if self._use_all_off_event:
            events = _compress_note_offs(events)

        if add_end:
            events.append(self.vocabulary.end_token)

        if as_ids:
            return self.vocabulary.to_ids(events)
        return events

    def decode(self, tokens):
        sequence = music_pb2.NoteSequence()
        sequence.ticks_per_quarter = STANDARD_PPQ

        notes_on = defaultdict(list)
        error_count = 0

        t = 0.
        current_beat = 0
        velocity = self._default_velocity
        for token in tokens:
            if isinstance(token, (int, np.integer)):
                token = self.vocabulary.from_id(token)
            if token not in self.vocabulary:
                raise RuntimeError(f'Invalid token: {token}')
            if not isinstance(token, tuple):
                continue
            event, value = token

            if event in ['SetTime', 'SetTimeNext']:
                if event == 'SetTimeNext':
                    current_beat += 1
                new_t = current_beat + value / self._units_per_beat
                if new_t > t:
                    t = new_t
                else:
                    error_count += 1
                continue

            if event == 'SetVelocity':
                velocity = (value - 1) * self._velocity_unit
            elif event in ['NoteOn', 'DrumOn']:
                note = sequence.notes.add()
                note.start_time = t
                note.pitch = value
                note.velocity = velocity
                note.is_drum = (event == 'DrumOn')
                notes_on[note.pitch].append(note)
            elif event in ['NoteOff', 'DrumOff']:
                if value == '*':
                    assert self._use_all_off_event

                    if not any(notes_on.values()):
                        error_count += 1

                    for note_list in notes_on.values():
                        for note in note_list:
                            note.end_time = t
                        note_list.clear()
                else:
                    try:
                        note = notes_on[value].pop()
                        note.end_time = t
                    except IndexError:
                        error_count += 1
        sequence.total_time = t

        if error_count:
            self._log_errors('Encountered {} errors'.format(error_count))

        # Handle hanging notes
        num_hanging = sum(len(lst) for lst in notes_on.values())
        if any(notes_on.values()):
            if self._errors == 'remove':
                self._log_errors(f'Removing {num_hanging} hanging note(s)')
                notes_filtered = list(sequence.notes)
                for hanging_notes in notes_on.values():
                    notes_filtered = [n for n in notes_filtered if n not in hanging_notes]
                del sequence.notes[:]
                sequence.notes.extend(notes_filtered)
            else:  # 'fix'
                self._log_errors(f'Ending {num_hanging} hanging note(s)')
                for hanging_notes in notes_on.values():
                    for note in hanging_notes:
                        note.end_time = sequence.total_time

        return sequence

    def _log_errors(self, message):
        if self._warn_on_errors:
            warnings.warn(message, RuntimeWarning)
        else:
            _LOGGER.debug(message)


class _NoteEventQueue:
    """
    A priority queue of note onsets and offsets.

    The queue is ordered according to time and pitch.
    Offsets come before onsets that occur at the same time, unless they correspond
    to the same note.
    """

    def __init__(self, sequence, quantization_step=None):
        """Initialize the queue.

        Args:
            sequence: A `NoteSequence`.
            quantization_step: The quantization step in seconds. If `None`, no
                quantization will be performed.
        """
        self._quantization_step = quantization_step

        # Build a heap of note onsets and offsets. For now, we only add the onsets;
        # an offset is added once the corresponding onset is popped. This is an easy
        # way to make sure that we never pop the offset first.
        # Below, the ID of the Note object is used to stop the heap algorithm from
        # comparing the Note itself, which would raise an exception.
        self._heap = [(self._quantize(note.start_time), True, note.pitch, note.is_drum,
                       id(note), note)
                      for note in sequence.notes]
        heapq.heapify(self._heap)

    def pop(self):
        """Return the next event from the queue.

        Returns:
            A tuple of the form `(time, note, is_onset)` where `time` is the time of the
            event (expressed as the number of quantization steps if applicable) and `note`
            is the corresponding `Note` object.
        """
        time, is_onset, _, _, _, note = heapq.heappop(self._heap)
        if is_onset:
            # Add the offset to the queue
            heapq.heappush(self._heap,
                           (self._quantize(note.end_time), False, note.pitch, note.is_drum,
                            id(note), note))

        return time, note, is_onset

    def __iter__(self):
        while self._heap:
            yield self.pop()

    def _quantize(self, value):
        if self._quantization_step:
            return int(value / self._quantization_step + 0.5)  # Round to nearest int
        return value
