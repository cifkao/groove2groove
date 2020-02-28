import io
import os
import threading

import flask
from magenta.music.protobuf.music_pb2 import NoteSequence
from museflow.config import Configuration
from museflow.note_sequence_utils import normalize_tempo
import tensorflow as tf

from groove2groove.io import NoteSequencePipeline
from groove2groove.models import roll2seq_style_transfer


app = flask.Flask(__name__,
                  static_folder='static/dist', static_url_path='/static',
                  instance_relative_config=True)
app.config.from_object('app.config')
app.config.from_pyfile('app.cfg', silent=True)

models = {}
model_graphs = {}
tf_lock = threading.Lock()


@app.before_first_request
def init_models():
    for model_name, model_cfg in app.config['MODELS'].items():
        logdir = os.path.join(app.config['MODEL_ROOT'], model_cfg.get('logdir', model_name))
        with open(os.path.join(logdir, 'model.yaml'), 'rb') as f:
            config = Configuration.from_yaml(f)

        model_graphs[model_name] = tf.Graph()
        with model_graphs[model_name].as_default():
            models[model_name] = config.configure(roll2seq_style_transfer.Experiment,
                                                  logdir=logdir, train_mode=False)
            models[model_name].trainer.load_variables(**model_cfg.get('load_variables', {}))


@app.route('/')
def index():
    return flask.render_template("index.html")


@app.route('/api/v1/style_transfer/<model_name>/', methods=['POST'])
def run_model(model_name):
    files = flask.request.files
    content_seq = NoteSequence.FromString(files['content_input'].read())
    style_seq = NoteSequence.FromString(files['style_input'].read())
    sample = flask.request.form.get('sample') == 'true'
    softmax_temperature = float(flask.request.form.get('softmax_temperature', 0.6))

    pipeline = NoteSequencePipeline(source_seq=content_seq, style_seq=style_seq,
                                    bars_per_segment=8, warp=True)
    with tf_lock, model_graphs[model_name].as_default():
        outputs = models[model_name].run(
                pipeline, sample=sample, softmax_temperature=softmax_temperature)
    output_seq = pipeline.postprocess(outputs)
    return flask.send_file(io.BytesIO(output_seq.SerializeToString()),
                           mimetype='application/protobuf')

@app.route('/api/v1/remix/', methods=['POST'])
def remix():
    files = flask.request.files
    content_seq = NoteSequence.FromString(files['content_sequence'].read())
    output_seq = NoteSequence.FromString(files['output_sequence'].read())
    # We will be merging content_seq into output_seq

    # Assume that output_seq has a constant tempo; warp content_seq to match it
    if output_seq.tempos and content_seq.tempos:
        content_seq = normalize_tempo(content_seq, output_seq.tempos[0].qpm)
    del output_seq.tempos[:]  # to avoid having double tempo information in the result

    # Shift instrument IDs to avoid collisions
    instrument_offset = max([0, *(x.instrument for x in [*output_seq.instrument_infos,
                                                         *output_seq.notes])])
    for collection in [content_seq.instrument_infos, content_seq.notes, content_seq.pitch_bends,
                       content_seq.control_changes]:
        for item in collection:
            item.instrument += instrument_offset

    total_time = max(content_seq.total_time, output_seq.total_time)
    output_seq.MergeFrom(content_seq)
    output_seq.total_time = total_time

    return flask.send_file(io.BytesIO(output_seq.SerializeToString()),
                           mimetype='application/protobuf')
