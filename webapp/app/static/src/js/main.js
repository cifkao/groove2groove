import '../scss/main.scss';

import { saveAs } from 'file-saver';
import * as mm from '@magenta/music/node/core';
import {NoteSequence} from '@magenta/music/node/protobuf';

const VISUALIZER_CONFIG = {
  pixelsPerTimeStep: 40,
  noteHeight: 4,
};
const INSTRUMENT_NAMES = [
  "Acoustic Grand Piano", "Bright Acoustic Piano", "Electric Grand Piano", "Honky-tonk Piano", "Electric Piano 1", "Electric Piano 2", "Harpsichord", "Clavinet", "Celesta", "Glockenspiel", "Music Box", "Vibraphone", "Marimba", "Xylophone", "Tubular Bells", "Dulcimer", "Drawbar Organ", "Percussive Organ", "Rock Organ", "Church Organ", "Reed Organ", "Accordion", "Harmonica", "Tango Accordion", "Acoustic Guitar (nylon)", "Acoustic Guitar (steel)", "Electric Guitar (jazz)", "Electric Guitar (clean)", "Electric Guitar (muted)", "Overdriven Guitar", "Distortion Guitar", "Guitar Harmonics", "Acoustic Bass", "Electric Bass (finger)", "Electric Bass (pick)", "Fretless Bass", "Slap Bass 1", "Slap Bass 2", "Synth Bass 1", "Synth Bass 2", "Violin", "Viola", "Cello", "Contrabass", "Tremolo Strings", "Pizzicato Strings", "Orchestral Harp", "Timpani", "String Ensemble 1", "String Ensemble 2", "Synth Strings 1", "Synth Strings 2", "Choir Aahs", "Voice Oohs", "Synth Choir", "Orchestra Hit", "Trumpet", "Trombone", "Tuba", "Muted Trumpet", "French Horn", "Brass Section", "Synth Brass 1", "Synth Brass 2", "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax", "Oboe", "English Horn", "Bassoon", "Clarinet", "Piccolo", "Flute", "Recorder", "Pan Flute", "Blown bottle", "Shakuhachi", "Whistle", "Ocarina", "Lead 1 (square)", "Lead 2 (sawtooth)", "Lead 3 (calliope)", "Lead 4 chiff", "Lead 5 (charang)", "Lead 6 (voice)", "Lead 7 (fifths)", "Lead 8 (bass + lead)", "Pad 1 (new age)", "Pad 2 (warm)", "Pad 3 (polysynth)", "Pad 4 (choir)", "Pad 5 (bowed)", "Pad 6 (metallic)", "Pad 7 (halo)", "Pad 8 (sweep)", "FX 1 (rain)", "FX 2 (soundtrack)", "FX 3 (crystal)", "FX 4 (atmosphere)", "FX 5 (brightness)", "FX 6 (goblins)", "FX 7 (echoes)", "FX 8 (sci-fi)", "Sitar", "Banjo", "Shamisen", "Koto", "Kalimba", "Bagpipe", "Fiddle", "Shanai", "Tinkle Bell", "Agogo", "Steel Drums", "Woodblock", "Taiko Drum", "Melodic Tom", "Synth Drum", "Reverse Cymbal", "Guitar Fret Noise", "Breath Noise", "Seashore", "Bird Tweet", "Telephone Ring", "Helicopter", "Applause", "Gunshot"
];
const DRUMS = 'DRUMS';

const data = {content: {}, style: {}, output: {}, remix: {}};

var controlCount = 0;  // counter used for assigning IDs to dynamically created controls

$('.after-content-loaded, .after-style-loaded, .after-generated').hide();
$('.container').fadeIn('fast');

$('input.midi-input').on('change', function() {
  const file = this.files[0];
  if (!file) return;

  const section = $(this).closest('[data-sequence-id]');
  const seqId = section.data('sequence-id');

  setControlsEnabled(section, false);
  $(this).siblings('.custom-file-label').text(this.files[0].name);

  mm.blobToNoteSequence(file).then(function(seq) {
    seq.filename = file.name;

    initSequence(section, seq);

    const maxTime = Math.ceil(seq.totalTime / 60 * seq.tempos[0].qpm);
    section.find('.start-time').val(0);
    section.find('.start-time').attr('max', maxTime - 1);
    section.find('.end-time').val(maxTime);
    section.find('.end-time').attr('max', maxTime);

    showMore(seqId + '-loaded');
  }).finally(() => setControlsEnabled(section, true));
});

$('.start-time, .end-time').on('change', handleSequenceEdit);

$('.play-button').on('click', function() {
  const section = $(this).closest('[data-sequence-id]');
  const seqId = section.data('sequence-id');

  if (!data[seqId].player)
    data[seqId].player = new mm.SoundFontPlayer(
      "https://storage.googleapis.com/magentadata/js/soundfonts/sgm_plus",
      undefined, null, null, {
        run: (note) => data[seqId].visualizer.redraw(note, true),
        stop: () => handlePlaybackStop(this)
    });

  if (data[seqId].player.isPlaying()) {
    data[seqId].player.stop();
    handlePlaybackStop(this);
  } else {
    section.find('.visualizer-container').scrollLeft(0);
    data[seqId].player.start(data[seqId].sequence);

    // Change button icon and text
    $(this).find('.oi').removeClass("oi-media-play").addClass("oi-media-stop");
    $(this).find('.text').text('Stop');
    $(this).attr('title', 'Stop');

    // Disable everything except for this button
    setControlsEnabled(section, false);
    $(this).attr('disabled', false);
  }
});

$('.save-button').on('click', function() {
  const section = $(this).closest('[data-sequence-id]');
  const seqId = section.data('sequence-id');

  const seq = data[seqId].sequence;
  saveAs(new File([mm.sequenceProtoToMidi(seq)], seq.filename));
});

$('.generate-button').on('click', function() {
  const section = $(this).closest('[data-sequence-id]');
  const seqId = section.data('sequence-id');

  // Create request
  const formData = new FormData();
  formData.append('content_input', new Blob([NoteSequence.encode(data['content'].sequence).finish()]), 'content_input');
  formData.append('style_input', new Blob([NoteSequence.encode(data['style'].sequence).finish()]), 'style_input');
  formData.append('sample', $('#samplingCheckbox').is(':checked'));
  formData.append('softmax_temperature', $('#samplingTemperature').val());

  setControlsEnabled(section, false);

  fetch('/api/v1/style_transfer/' + $('#modelName').val() + '/', {method: 'POST', body: formData})
    .then((response) => response.arrayBuffer())
    .then(function (buffer) {
      // Decode the protobuffer
      const seq = NoteSequence.decode(new Uint8Array(buffer));

      // Assign a new filename based on the input filenames
      seq.filename = data['content'].sequence.filename.replace(/\.[^.]+$/, '') + '__' + data['style'].sequence.filename;

      // Display the sequence
      initSequence(section, seq);
      showMore('generated');
    })
    .finally(() => setControlsEnabled(section, true));
});

function initSequence(section, seq) {
  const seqId = section.data('sequence-id');
  data[seqId].fullSequence = seq;
  data[seqId].trimmedSequence = seq;
  data[seqId].sequence = seq;

  // Show piano roll
  const svg = section.find('svg')[0];
  data[seqId].visualizer = new mm.PianoRollSVGVisualizer(seq, svg, VISUALIZER_CONFIG);
  section.find('.visualizer-container').scrollLeft(0);

  if (seqId == 'remix')
    return;

  // Add instrument checkboxes
  section.find('.instrument-toggles').empty();
  getSequencePrograms(seq).forEach(function (program) {
    const controlId = 'checkbox' + (controlCount++);
    const instrument = program == DRUMS ? 'Drums' : INSTRUMENT_NAMES[program];
    const checkbox = $('<input type="checkbox" class="form-check-input" checked>')
        .attr('id', controlId).val(program)
        .on('change', handleSequenceEdit);
    $('<div class="form-check form-check-inline"></div>')
      .append(checkbox)
      .append($('<label class="form-check-label"></label>').attr('for', controlId).text(instrument))
      .appendTo(section.find('.instrument-toggles'));
  });

  // Update the remix section if needed
  if (seqId == 'content' || seqId == 'output') {
    if (seqId == 'content') {
      mirrorControls(section.find('.instrument-toggles'), $('#remixContentToggles'));
    } else if (seqId == 'output') {
      mirrorControls(section.find('.instrument-toggles'), $('#remixOutputToggles'));
    }

    initRemix();
  }
}

function handleSequenceEdit() {
  const section = $(this).closest('[data-sequence-id]');
  const seqId = section.data('sequence-id');
  if (seqId == 'remix') {
    updateRemix();
    return;
  }

  var seq = data[seqId].fullSequence;

  const startTime = section.find('.start-time').val();
  const endTime = section.find('.end-time').val();
  if (startTime !== undefined && endTime !== undefined) {
    seq = mm.sequences.trim(seq,
                            startTime * 60 / seq.tempos[0].qpm,
                            endTime * 60 / seq.tempos[0].qpm,
                            true);
  } else {
    seq = mm.sequences.clone(seq);
  }
  data[seqId].trimmedSequence = seq;

  const programs = getSelectedPrograms(section.find('.instrument-toggles :checked'));
  filterSequence(seq, programs, true);  // filter in place

  updateSequence(seqId, seq);

  if ($(this).hasClass('start-time'))
    section.find('.visualizer-container').scrollLeft(0);
}

function initRemix() {
  $('#remixContentToggles input').prop('checked', false);
  if (!data['output'].trimmedSequence) return;
  initSequence($('[data-sequence-id=remix]'), data['output'].trimmedSequence);
}

function updateRemix() {
  const contentPrograms = getSelectedPrograms($('#remixContentToggles :checked'));
  const outputPrograms = getSelectedPrograms($('#remixOutputToggles :checked'));
  const contentSeq = filterSequence(data['content'].trimmedSequence, contentPrograms);
  const outputSeq = filterSequence(data['output'].trimmedSequence, outputPrograms);

  // Create request
  const formData = new FormData();
  formData.append('content_sequence', new Blob([NoteSequence.encode(contentSeq).finish()]), 'content_sequence');
  formData.append('output_sequence', new Blob([NoteSequence.encode(outputSeq).finish()]), 'output_sequence');

  const section = $('.section[data-sequence-id=remix]');
  setControlsEnabled(section, false);

  fetch('/api/v1/remix/', {method: 'POST', body: formData})
    .then((response) => response.arrayBuffer())
    .then(function (buffer) {
      // Decode the protobuffer
      const seq = NoteSequence.decode(new Uint8Array(buffer));

      // Assign a new filename based on the input filenames
      seq.filename = outputSeq.filename.replace(/\.[^.]+$/, '') + '__remix.mid';

      // Display the sequence
      updateSequence('remix', seq);
    })
    .finally(() => setControlsEnabled(section, true));
}

function updateSequence(seqId, seq) {
  data[seqId].sequence = seq;
  data[seqId].visualizer.noteSequence = seq;
  data[seqId].visualizer.clear();
  data[seqId].visualizer.redraw();
}

function setControlsEnabled(section, enabled) {
  section.find('input, button, select').attr('disabled', !enabled);
}

function handlePlaybackStop(button) {
  $(button).find('.oi').removeClass("oi-media-stop").addClass("oi-media-play");
  $(button).find('.text').text('Play');
  $(button).attr('title', 'Play');

  const section = $(button).closest('[data-sequence-id]');
  setControlsEnabled(section, true);
}

function showMore(label) {
  const elements = $('.after-' + label);
  if (!elements.is(":visible")) {
    elements.fadeIn(
      'fast',
      () => elements.filter('.visualizer-card')[0].scrollIntoView({behavior: 'smooth'})
    );
  }
}

function getSequencePrograms(sequence) {
  const programs = {};
  sequence.notes.forEach(function(note) {
    const program = note.isDrum ? DRUMS : note.program;
    programs[program] = true;
  });
  return Object.keys(programs).sort();
}

function getSelectedPrograms(checkboxes) {
  return checkboxes.map((_, checkbox) => $(checkbox).val())
    .map((_, p) => isNaN(p) ? p : parseInt(p))
    .get();
}

function filterSequence(sequence, programs, inPlace) {
  const programsMap = {};
  programs.forEach((p) => {programsMap[p] = true;});

  // Make a copy if needed
  const filtered = inPlace ? sequence : mm.sequences.clone(sequence);
  const notes = sequence.notes;
  filtered.notes = [];
  notes.forEach(function(note) {
    if ((note.isDrum && programsMap[DRUMS]) || programsMap[note.program])
      filtered.notes.push(note);
  });

  return filtered;
}

function mirrorControls(source, target) {
  target.empty();
  source.children().clone(true).appendTo(target);
  target.find('input, button, select')
    .attr('id', (_, id) => id + '_' + controlCount);
  target.find('label')
    .attr('for', (_, id) => id + '_' + controlCount);
  controlCount++;
}
