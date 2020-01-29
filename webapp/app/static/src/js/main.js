import '../scss/main.scss';

import { saveAs } from 'file-saver';
import * as Tone from 'tone';
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

const data = {content: {}, style: {}, output: {}};

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
      Tone.Master, null, null, {
        run: (note) => data[seqId].visualizer.redraw(note, true),
        stop: () => handlePlaybackStop(this)
		});

  if (data[seqId].player.isPlaying()) {
    data[seqId].player.stop();
    handlePlaybackStop(this);
  } else {
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

  fetch('/api/v1/style_transfer/v02d_drums01/', {method: 'POST', body: formData})
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
  data[seqId].sequence = seq;

  // Show piano roll
  const svg = section.find('svg')[0];
  data[seqId].visualizer = new mm.PianoRollSVGVisualizer(seq, svg, VISUALIZER_CONFIG);

  // Add instrument check boxes
  section.find('.instrument-toggles').empty();
  getSequencePrograms(seq).forEach(function (program) {
    var controlId = 'checkbox' + (controlCount++);
    var instrument = program == DRUMS ? 'Drums' : INSTRUMENT_NAMES[program];
    var checkbox = $('<input type="checkbox" class="form-check-input" checked>')
        .attr('id', controlId).val(program)
        .on('change', handleSequenceEdit);
    $('<div class="form-check form-check-inline"></div>')
      .append(checkbox)
      .append($('<label class="form-check-label"></label>').attr('for', controlId).text(instrument))
      .appendTo(section.find('.instrument-toggles'));
  });
}

function handleSequenceEdit() {
  const section = $(this).closest('[data-sequence-id]');
  const seqId = section.data('sequence-id');
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

  const programs = section.find(".instrument-toggles :checked")
    .map((_, checkbox) => $(checkbox).val())
    .map((_, p) => isNaN(p) ? p : parseInt(p))
    .get();
  filterSequence(seq, programs, true);  // filter in place

  data[seqId].sequence = seq;
  data[seqId].visualizer.noteSequence = seq;
  data[seqId].visualizer.clear();
  data[seqId].visualizer.redraw();
}

function setControlsEnabled(section, enabled) {
  section.find('input, button').attr('disabled', !enabled);
}

function handlePlaybackStop(button) {
  $(button).find('.oi').removeClass("oi-media-stop").addClass("oi-media-play");
  $(button).find('.text').text('Play');
  $(button).attr('title', 'Play');

  const section = $(button).closest('[data-sequence-id]');
  setControlsEnabled(section, true);
}

function showMore(label) {
  if (!$('.after-' + label).is(":visible")) {
    $('.after-' + label).fadeIn('slow');
    $('.after-' + label).last()[0].scrollIntoView({behavior: 'smooth'});
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

function filterSequence(sequence, programs, inPlace) {
  const programsMap = {};
  programs.forEach((p) => {programsMap[p] = true;});

  // Make a (shallow) copy if needed
  const filtered = inPlace ? sequence : Object.assign({}, sequence);
  const notes = sequence.notes;
  filtered.notes = [];
  notes.forEach(function(note) {
    if ((note.isDrum && programsMap[DRUMS]) || programsMap[note.program])
      filtered.notes.push(note);
  });

  return filtered;
}
