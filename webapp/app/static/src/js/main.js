import '../scss/main.scss';

import { saveAs } from 'file-saver';
import * as Tone from 'tone';
import * as mm from '@magenta/music/node/core';
import {NoteSequence} from '@magenta/music/node/protobuf';

const VISUALIZER_CONFIG = {
  pixelsPerTimeStep: 40,
  noteHeight: 4,
};

const data = {content: {}, style: {}, output: {}};

$('.after-content-loaded, .after-style-loaded, .after-generated').hide();
$('.container').fadeIn('fast');

$('input.midi-input').on('change', function() {
  const file = this.files[0];
  const section = $(this).closest('[data-sequence-id]');
  const seqId = section.data('sequence-id');
  const svg = section.find('svg')[0];
  const controls = section.find('.play-button, .save-button');

  controls.attr('disabled', true);
  $(this).siblings('.custom-file-label').text(this.files[0].name);

  mm.blobToNoteSequence(file).then(function(seq) {
    seq.filename = file.name;

    data[seqId].fullSequence = seq;
    data[seqId].sequence = seq;
    data[seqId].visualizer = new mm.PianoRollSVGVisualizer(seq, svg, VISUALIZER_CONFIG);

    const maxTime = Math.ceil(seq.totalTime / 60 * data[seqId].fullSequence.tempos[0].qpm);
    section.find('.start-time').val(0);
    section.find('.start-time').attr('max', maxTime - 1);
    section.find('.end-time').val(maxTime);
    section.find('.end-time').attr('max', maxTime);
    showMore(seqId + '-loaded');
  }).finally(() => controls.attr('disabled', false));
});

$('.start-time, .end-time').on('change', function() {
  const section = $(this).closest('[data-sequence-id]');
  const seqId = section.data('sequence-id');
  const startTime = section.find('.start-time').val();
  const endTime = section.find('.end-time').val();

  data[seqId].sequence = mm.sequences.trim(
    data[seqId].fullSequence,
    startTime * 60 / data[seqId].fullSequence.tempos[0].qpm,
    endTime * 60 / data[seqId].fullSequence.tempos[0].qpm,
    true);
  data[seqId].visualizer.noteSequence = data[seqId].sequence;
  data[seqId].visualizer.clear();
  data[seqId].visualizer.redraw();
});

$('.play-button').on('click', function() {
  const section = $(this).closest('[data-sequence-id]');
  const seqId = section.data('sequence-id');

  if (!data[seqId].player)
    data[seqId].player = new mm.SoundFontPlayer(
      "https://storage.googleapis.com/magentadata/js/soundfonts/sgm_plus",
      Tone.Master, null, null, {
        run: (note) => data[seqId].visualizer.redraw(note),
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

  // Disable the controls for this sequence
  const controls = section.find('.play-button, .save-button, .generate-button, #samplingCheckbox, #samplingTemperature');
  controls.attr('disabled', true);

  // Create request
  const formData = new FormData();
  formData.append('content_input', new Blob([NoteSequence.encode(data['content'].sequence).finish()]), 'content_input');
  formData.append('style_input', new Blob([NoteSequence.encode(data['style'].sequence).finish()]), 'style_input');
  formData.append('sample', $('#samplingCheckbox').is(':checked'));
  formData.append('softmax_temperature', $('#samplingTemperature').val());

  fetch('/api/v1/style_transfer/v02d_drums01/', {method: 'POST', body: formData})
    .then((response) => response.arrayBuffer())
    .then(function (buffer) {
      // Decode the protobuffer
      const seq = NoteSequence.decode(new Uint8Array(buffer));

      // Assign a new filename based on the input filenames
      seq.filename = data['content'].sequence.filename.replace(/\.[^.]+$/, '') + '__' + data['style'].sequence.filename;

      // Display the sequence
      data[seqId].fullSequence = seq;
      data[seqId].sequence = seq;
      const svg = section.find('svg')[0];
      data[seqId].visualizer = new mm.PianoRollSVGVisualizer(seq, svg, VISUALIZER_CONFIG);

      showMore('generated');
    })
    .finally(() => controls.attr('disabled', false));
});

function handlePlaybackStop(button) {
  $(button).find('.oi').removeClass("oi-media-stop").addClass("oi-media-play");
  $(button).find('.text').text('Play');
  $(button).attr('title', 'Play');
}

function showMore(label) {
  if (!$('.after-' + label).is(":visible")) {
    $('.after-' + label).fadeIn('slow');
    $('.visualizer-container.after-' + label)[0].scrollIntoView({behavior: 'smooth'});
  }
}
