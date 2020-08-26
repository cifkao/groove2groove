import io
import logging
import os
import threading

from confugue import Configuration
import flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from note_seq.protobuf.music_pb2 import NoteSequence
from museflow.note_sequence_utils import normalize_tempo
import numpy as np
import tensorflow as tf
import werkzeug.exceptions
from werkzeug.middleware.proxy_fix import ProxyFix

from groove2groove.io import NoteSequencePipeline
from groove2groove.models import roll2seq_style_transfer


app = flask.Flask(__name__,
                  instance_relative_config=True)
app.config.from_object('app.config')
app.config.from_pyfile('app.cfg', silent=True)
if 'STATIC_FOLDER' in app.config:
    app.static_folder = app.config['STATIC_FOLDER']
    app.static_url_path = '/'

app.wsgi_app = ProxyFix(app.wsgi_app, **app.config.get('PROXY_FIX', {}))
limiter = Limiter(app, key_func=get_remote_address, headers_enabled=True, **app.config.get('LIMITER', {}))
CORS(app, **app.config.get('CORS', {}))

logging.getLogger('tensorflow').handlers.clear()

models = {}
model_graphs = {}
tf_lock = threading.Lock()


if app.config.get('SERVE_STATIC_FILES', False):
    @app.route("/", defaults={'path': 'index.html'})
    @app.route("/<path:path>")
    def root(path):
        return flask.send_from_directory(app.static_folder, path)


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


@app.route('/api/v1/style_transfer/<model_name>/', methods=['POST'])
@limiter.limit(app.config.get('MODEL_RATE_LIMIT', None))
def run_model(model_name):
    files = flask.request.files
    content_seq = NoteSequence.FromString(files['content_input'].read())
    style_seq = NoteSequence.FromString(files['style_input'].read())
    sample = flask.request.form.get('sample') == 'true'
    softmax_temperature = float(flask.request.form.get('softmax_temperature', 0.6))

    sanitize_ns(content_seq)
    sanitize_ns(style_seq)

    content_stats = ns_stats(content_seq)
    if content_stats['beats'] > app.config.get('MAX_CONTENT_INPUT_BEATS', np.inf) + 1e-2:
        return error_response('CONTENT_INPUT_TOO_LONG')
    if content_stats['notes'] > app.config.get('MAX_CONTENT_INPUT_NOTES', np.inf):
        return error_response('CONTENT_INPUT_TOO_MANY_NOTES')

    style_stats = ns_stats(style_seq)
    if style_stats['beats'] > app.config.get('MAX_STYLE_INPUT_BEATS', np.inf) + 1e-2:
        return error_response('STYLE_INPUT_TOO_LONG')
    if style_stats['notes'] > app.config.get('MAX_STYLE_INPUT_NOTES', np.inf):
        return error_response('STYLE_INPUT_TOO_MANY_NOTES')
    if style_stats['programs'] > app.config.get('MAX_STYLE_INPUT_PROGRAMS', np.inf):
        return error_response('STYLE_INPUT_TOO_MANY_INSTRUMENTS')

    run_options = None
    if 'BATCH_TIMEOUT' in app.config:
        run_options = tf.RunOptions(timeout_in_ms=int(app.config['BATCH_TIMEOUT'] * 1000))

    pipeline = NoteSequencePipeline(source_seq=content_seq, style_seq=style_seq,
                                    bars_per_segment=8, warp=True)
    try:
        with tf_lock, model_graphs[model_name].as_default():
            outputs = models[model_name].run(
                    pipeline, sample=sample, softmax_temperature=softmax_temperature,
                    normalize_velocity=True, options=run_options)
    except tf.errors.DeadlineExceededError:
        return error_response('MODEL_TIMEOUT', status_code=500)
    output_seq = pipeline.postprocess(outputs)
    return flask.send_file(io.BytesIO(output_seq.SerializeToString()),
                           mimetype='application/protobuf')


@app.errorhandler(werkzeug.exceptions.HTTPException)
def http_error_handler(error):
    response = error.get_response()
    response.data = flask.json.dumps({
        'code': error.code,
        'error': error.name,
        'description': error.description
    })
    response.content_type = 'application/json';
    return response


def error_response(error, status_code=400):
    response = flask.make_response(flask.json.dumps({'error': error}), status_code)
    response.content_type = 'application/json';
    return response;


def sanitize_ns(ns):
    if not ns.tempos:
        tempo = ns.tempos.add()
        tempo.time = 0
        tempo.qpm = 120
    if not ns.time_signatures:
        ts = ns.time_signatures.add()
        time_signature.time = 0
        time_signature.numerator = 4
        time_signature.denominator = 4

    for note in ns.notes:
        note.end_time = max(note.start_time, note.end_time)
        ns.total_time = max(ns.total_time, note.end_time)

    for collection in [ns.tempos, ns.time_signatures, ns.key_signatures, ns.pitch_bends,
                       ns.control_changes, ns.text_annotations, ns.section_annotations]:
        filtered = [event for event in collection if event.time <= ns.total_time]
        del collection[:]
        collection.extend(filtered)


def ns_stats(ns):
    stats = {'beats': 0}

    tempos = list(ns.tempos)
    tempos.append(NoteSequence.Tempo(time=ns.total_time + 1e-4))
    tempos.sort(key=lambda x: x.time)
    for i in range(len(tempos) - 1):
       stats['beats'] += (tempos[i + 1].time - tempos[i].time) * tempos[i].qpm / 60

    stats['programs'] = len(set((note.program, note.is_drum) for note in ns.notes))
    stats['notes'] = len(ns.notes)

    return stats
