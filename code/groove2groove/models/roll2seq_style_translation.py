#!/usr/bin/env python3
import argparse
import logging
import os

import coloredlogs
import numpy as np
import tensorflow as tf
import tqdm
from magenta.music.protobuf import music_pb2
from museflow.components import EmbeddingLayer, RNNDecoder, RNNLayer
from museflow.config import Configuration, configurable
from museflow.model_utils import (DatasetManager, create_train_op, make_simple_dataset,
                                  prepare_train_and_val_data, set_random_seed)
from museflow.nn.rnn import InputWrapper
from museflow.note_sequence_utils import filter_sequence
from museflow.trainer import BasicTrainer
from museflow.vocabulary import Vocabulary

from groove2groove.io import EvalPipeline, MidiPipeline, TrainLoader
from groove2groove.models.common import CNN

_LOGGER = logging.getLogger(__name__)


@configurable(pass_kwargs=False)
class Model:

    def __init__(self, dataset_manager, train_mode, vocabulary, style_vocabulary,
                 sampling_seed=None):
        self._train_mode = train_mode
        self._is_training = tf.placeholder_with_default(False, [], name='is_training')

        self.dataset_manager = dataset_manager

        inputs, style_id, decoder_inputs, decoder_targets = self.dataset_manager.get_next()

        cnn = self._cfg['encoder_cnn'].configure(CNN,
                                                 training=self._is_training,
                                                 name='encoder_cnn')
        rnn = self._cfg['encoder_rnn'].configure(RNNLayer,
                                                 training=self._is_training,
                                                 name='encoder_rnn')
        encoder_states, _ = rnn(cnn(inputs))

        embeddings = self._cfg['embedding_layer'].configure(EmbeddingLayer,
                                                            input_size=len(vocabulary),
                                                            name='embedding_layer')

        style_embeddings = self._cfg['embedding_layer'].configure(EmbeddingLayer,
                                                                  input_size=len(style_vocabulary),
                                                                  name='embedding_layer')
        self.style_vector = style_embeddings.embed(style_id)

        def cell_wrap_fn(cell):
            """Wrap the RNN cell in order to pass the style embedding as input."""
            cell = InputWrapper(cell, input_fn=lambda _: self.style_vector)
            return cell

        with tf.variable_scope('attention'):
            attention = self._cfg['attention_mechanism'].maybe_configure(memory=encoder_states)

        self.decoder = self._cfg['decoder'].configure(RNNDecoder,
                                                      vocabulary=vocabulary,
                                                      embedding_layer=embeddings,
                                                      attention_mechanism=attention,
                                                      pre_attention=True,
                                                      training=self._is_training,
                                                      cell_wrap_fn=cell_wrap_fn)

        # Build the training version of the decoder and the training ops
        self.training_ops = None
        if train_mode:
            _, self.loss = self.decoder.decode_train(decoder_inputs, decoder_targets)
            self.training_ops = self._make_train_ops()

        # Build the sampling and greedy version of the decoder
        batch_size = tf.shape(inputs)[0]
        self.softmax_temperature = tf.placeholder(tf.float32, [], name='softmax_temperature')
        self.sample_outputs, self.sample_final_state = self.decoder.decode(
            mode='sample',
            softmax_temperature=self.softmax_temperature,
            batch_size=batch_size,
            random_seed=sampling_seed)
        self.greedy_outputs, self.greedy_final_state = self.decoder.decode(
            mode='greedy',
            batch_size=batch_size)

        self._inputs = {
            'content_input': inputs, 'style_id': style_id,
            'style_embedding': self.style_vector, 'softmax_temperature': self.softmax_temperature,
        }

    def _make_train_ops(self):
        train_op = self._cfg['training'].configure(create_train_op, loss=self.loss)
        init_op = tf.global_variables_initializer()

        tf.summary.scalar('train/loss', self.loss)
        train_summary_op = tf.summary.merge_all()

        return BasicTrainer.TrainingOps(loss=self.loss,
                                        train_op=train_op,
                                        init_op=init_op,
                                        summary_op=train_summary_op,
                                        training_placeholder=self._is_training)

    def run(self, session, dataset, sample=False, softmax_temperature=1.):
        _, output_ids_tensor = self.sample_outputs if sample else self.greedy_outputs

        return self.dataset_manager.run_over_dataset(
            session, output_ids_tensor, dataset,
            feed_dict={self.softmax_temperature: softmax_temperature},
            concat_batches=True)


@configurable(pass_kwargs=False)
class Experiment:

    def __init__(self, logdir, train_mode, sampling_seed=None):
        random_seed = self._cfg.get('random_seed', None)
        set_random_seed(random_seed)
        self.logdir = logdir

        self.input_encoding = self._cfg['input_encoding'].configure()
        self.output_encoding = self._cfg['output_encoding'].configure()
        with open(self._cfg.get('style_list')) as f:
            self.style_vocabulary = Vocabulary(
                [line.rstrip('\n') for line in f],
                pad_token=None, start_token=None, end_token=None)

        num_rows = getattr(self.input_encoding, 'num_rows', None)
        self.input_shapes = (([num_rows, None] if num_rows else [None]), [], [None], [None])
        self.input_types = (tf.float32 if num_rows else tf.int32, tf.int32, tf.int32, tf.int32)
        self.dataset_manager = DatasetManager(
            output_types=self.input_types,
            output_shapes=tuple([None, *shape] for shape in self.input_shapes))

        self.model = self._cfg['model'].configure(Model,
                                                  dataset_manager=self.dataset_manager,
                                                  train_mode=train_mode,
                                                  vocabulary=self.output_encoding.vocabulary,
                                                  style_vocabulary=self.style_vocabulary,
                                                  sampling_seed=sampling_seed)

        self._load_checkpoint = self._cfg.get('load_checkpoint', None)
        if self._load_checkpoint and self.model.training_ops is not None:
            self.model.training_ops.init_op = ()

        self.trainer = self._cfg['trainer'].configure(BasicTrainer,
                                                      session=tf.Session(),
                                                      dataset_manager=self.dataset_manager,
                                                      training_ops=self.model.training_ops,
                                                      logdir=logdir,
                                                      write_summaries=train_mode)

        if train_mode:
            # Configure the dataset manager with the training and validation data.

            train_loader = self._cfg['train_data'].configure(
                TrainLoader, random_seed=random_seed, mode='style_id')
            val_loader = self._cfg['val_data'].configure(
                TrainLoader, random_seed=random_seed, reseed=True, mode='style_id')

            self._cfg['data_prep'].configure(
                prepare_train_and_val_data,
                dataset_manager=self.dataset_manager,
                train_generator=self._load_data(train_loader, training=True),
                val_generator=self._load_data(val_loader),
                output_types=self.input_types,
                output_shapes=self.input_shapes)

    def train(self, args):
        del args
        if self._load_checkpoint:
            self.trainer.load_variables(checkpoint_file=self._load_checkpoint)

        _LOGGER.info('Starting training.')
        self.trainer.train()

    def run_midi(self, args):
        self.run_test(args, midi=True)

    def run_test(self, args, midi=False):
        self.trainer.load_variables(checkpoint_file=args.checkpoint)

        if midi:
            pipeline = MidiPipeline(source_path=args.source_file, style_path=args.style_file,
                                    bars_per_segment=args.bars_per_segment, warp=True)
        else:
            pipeline = EvalPipeline(source_db_path=args.source_db, style_db_path=args.style_db,
                                    key_pairs_path=args.key_pairs)

        dataset = make_simple_dataset(
            self._load_data(tqdm.tqdm(pipeline)),
            output_types=self.input_types,
            output_shapes=self.input_shapes,
            batch_size=args.batch_size)
        output_ids = self.model.run(
            self.trainer.session, dataset, args.sample, args.softmax_temperature)
        sequences = [self.output_encoding.decode(ids) for ids in output_ids]
        pipeline.save(sequences, args.output_file if midi else args.output_db)

    def _load_data(self, loader, training=False, encode=True):
        max_target_len = self._cfg.get('max_target_length', np.inf)
        filters = sorted(self._cfg.get('style_note_filters').items())
        if len(filters) != 1:
            raise ValueError('Exactly one style note filter must be specified')

        def generator():
            i = 0
            long_skip_count = 0
            empty_count = 0
            for src_seq, style, tgt_seq_all in loader:
                for _, filter_kwargs in filters:
                    tgt_seq = None
                    if tgt_seq_all is not None:
                        tgt_seq = music_pb2.NoteSequence()
                        tgt_seq.CopyFrom(tgt_seq_all)
                        filter_sequence(tgt_seq, **filter_kwargs)
                        if training and tgt_seq is not None and len(tgt_seq.notes) > max_target_len:
                            long_skip_count += 1
                            continue

                    if training and not src_seq.notes:
                        empty_count += 1
                        continue

                    if encode:
                        src_encoded = self.input_encoding.encode(src_seq)
                        tgt_encoded = self.output_encoding.encode(
                            tgt_seq, add_start=True, add_end=True) if tgt_seq is not None else []
                        style_encoded = self.style_vocabulary.to_id(style)
                        yield src_encoded, style_encoded, tgt_encoded[:-1], tgt_encoded[1:]
                    else:
                        yield src_seq, style, tgt_seq

                    i += 1

            if training:
                _LOGGER.info(f'Done loading data: {i} examples; '
                             f'skipped: {long_skip_count} too long, {empty_count} empty')

        return generator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--logdir', type=str, required=True, help='model directory')
    parser.set_defaults(train_mode=False, sampling_seed=None)
    subparsers = parser.add_subparsers(title='action')

    subparser = subparsers.add_parser('train')
    subparser.set_defaults(func=Experiment.train, train_mode=True)

    subparser = subparsers.add_parser('run-midi')
    subparser.set_defaults(func=Experiment.run_midi, filters='program')
    subparser.add_argument('source_file', metavar='INPUTFILE')
    subparser.add_argument('style_file', metavar='STYLEFILE')
    subparser.add_argument('output_file', metavar='OUTPUTFILE')
    subparser.add_argument('--checkpoint', default=None, type=str)
    subparser.add_argument('--batch-size', default=1, type=int)
    subparser.add_argument('--sample', action='store_true')
    subparser.add_argument('--softmax-temperature', default=1., type=float)
    subparser.add_argument('--seed', type=int, dest='sampling_seed')
    subparser.add_argument('--filters', choices=['training', 'program'], default='program',
                           help='how to filter the input; training: use the same filters as '
                           'during training; program: filter by MIDI program')
    subparser.add_argument('-b', '--bars-per-segment', default=8, type=int)

    subparser = subparsers.add_parser('run-test')
    subparser.set_defaults(func=Experiment.run_test)
    subparser.add_argument('source_db', metavar='INPUTDB')
    subparser.add_argument('style_db', metavar='STYLEDB')
    subparser.add_argument('key_pairs', metavar='KEYPAIRS')
    subparser.add_argument('output_db', metavar='OUTPUTDB')
    subparser.add_argument('--checkpoint', default=None, type=str)
    subparser.add_argument('--batch-size', default=32, type=int)
    subparser.add_argument('--sample', action='store_true')
    subparser.add_argument('--softmax-temperature', default=1., type=float)
    subparser.add_argument('--seed', type=int, dest='sampling_seed')
    subparser.add_argument('--filters', choices=['training', 'program'], default='program',
                           help='how to filter the input; training: use the same filters as '
                           'during training; program: filter by MIDI program')

    args = parser.parse_args()

    config_file = os.path.join(args.logdir, 'model.yaml')
    with open(config_file, 'rb') as f:
        config = Configuration.from_yaml(f)
    _LOGGER.debug(config)

    experiment = config.configure(Experiment,
                                  logdir=args.logdir, train_mode=args.train_mode,
                                  sampling_seed=args.sampling_seed)
    args.func(experiment, args)


if __name__ == '__main__':
    coloredlogs.install(level='DEBUG', logger=logging.root, isatty=True)
    logging.getLogger('tensorflow').handlers.clear()
    main()
