#!/usr/bin/env python3
import argparse
import logging
import os

import coloredlogs
import numpy as np
import tensorflow as tf
import tqdm
from confugue import Configuration, configurable
from museflow.components import EmbeddingLayer, RNNDecoder, RNNLayer
from museflow.model_utils import (DatasetManager, create_train_op, make_simple_dataset,
                                  prepare_train_and_val_data, set_random_seed)
from museflow.nn.rnn import InputWrapper
from museflow.note_sequence_utils import filter_sequence, set_note_fields
from museflow.trainer import BasicTrainer
from note_seq.protobuf import music_pb2

from groove2groove.io import EvalPipeline, MidiPipeline, TrainLoader
from groove2groove.models.common import CNN

_LOGGER = logging.getLogger(__name__)


@configurable
class Model:

    def __init__(self, dataset_manager, train_mode, vocabulary, sampling_seed=None):
        self._train_mode = train_mode
        self._is_training = tf.placeholder_with_default(False, [], name='is_training')

        self.dataset_manager = dataset_manager

        inputs, style_inputs, decoder_inputs, decoder_targets = self.dataset_manager.get_next()

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

        style_cnn = self._cfg['style_encoder_cnn'].configure(CNN,
                                                             training=self._is_training,
                                                             name='style_encoder_cnn')
        style_rnn = self._cfg['style_encoder_rnn'].configure(RNNLayer,
                                                             training=self._is_training,
                                                             name='style_encoder_rnn')
        style_projection = self._cfg['style_projection'].maybe_configure(tf.layers.Dense,
                                                                         name='style_projection')
        _, style_final_state = style_rnn(style_cnn(embeddings.embed(style_inputs)))
        self.style_vector = (style_projection(style_final_state) if style_projection
                             else style_final_state)
        style_dropout = self._cfg['style_dropout'].maybe_configure(tf.layers.Dropout)
        if style_dropout:
            self.style_vector = style_dropout(self.style_vector, training=self._is_training)

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
            'content_input': inputs, 'style_input': style_inputs,
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

    def run(self, session, dataset, sample=False, softmax_temperature=1., options=None):
        _, output_ids_tensor = self.sample_outputs if sample else self.greedy_outputs

        return self.dataset_manager.run_over_dataset(
            session, output_ids_tensor, dataset,
            feed_dict={self.softmax_temperature: softmax_temperature},
            concat_batches=True,
            options=options)


@configurable
class Experiment:

    def __init__(self, logdir, train_mode, sampling_seed=None):
        random_seed = self._cfg.get('random_seed', None)
        set_random_seed(random_seed)
        self.logdir = logdir

        self.input_encoding = self._cfg['input_encoding'].configure()
        self.output_encoding = self._cfg['output_encoding'].configure()

        num_rows = getattr(self.input_encoding, 'num_rows', None)
        self.input_shapes = (([num_rows, None] if num_rows else [None]), [None], [None], [None])
        self.input_types = (tf.float32 if num_rows else tf.int32, tf.int32, tf.int32, tf.int32)
        self.dataset_manager = DatasetManager(
            output_types=self.input_types,
            output_shapes=tuple([None, *shape] for shape in self.input_shapes))

        self.model = self._cfg['model'].configure(Model,
                                                  dataset_manager=self.dataset_manager,
                                                  train_mode=train_mode,
                                                  vocabulary=self.output_encoding.vocabulary,
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
            train_loader = self._cfg['train_data'].configure(TrainLoader, random_seed=random_seed)
            val_loader = self._cfg['val_data'].configure(TrainLoader, random_seed=random_seed,
                                                         reseed=True)
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
            self.trainer.load_variables(
                checkpoint_file=os.path.join(self.logdir, self._load_checkpoint))

        _LOGGER.info('Starting training.')
        self.trainer.train()

    def run_midi(self, args):
        pipeline = MidiPipeline(source_path=args.source_file, style_path=args.style_file,
                                bars_per_segment=args.bars_per_segment, warp=True)
        sequences = self._run_cli(args, pipeline)
        pipeline.save(sequences, args.output_file)

    def run_test(self, args):
        pipeline = EvalPipeline(source_db_path=args.source_db, style_db_path=args.style_db,
                                key_pairs_path=args.key_pairs)
        sequences = self._run_cli(args, pipeline)
        pipeline.save(sequences, args.output_db)

    def _run_cli(self, args, pipeline):
        self.trainer.load_variables(checkpoint_name='latest', checkpoint_file=args.checkpoint)
        return self.run(pipeline, batch_size=args.batch_size, filters=args.filters,
                        sample=args.sample, softmax_temperature=args.softmax_temperature)

    def run(self, pipeline, batch_size=None, filters='program', sample=False,
            softmax_temperature=1., normalize_velocity=False, options=None):
        metadata_list = []  # gather metadata about each item of the dataset
        apply_filters = '__program__' if filters == 'program' else True
        dataset = make_simple_dataset(
            self._load_data(tqdm.tqdm(pipeline), apply_filters=apply_filters,
                            normalize_velocity=normalize_velocity,
                            metadata_list=metadata_list),
            output_types=self.input_types,
            output_shapes=self.input_shapes,
            batch_size=batch_size or self._cfg['data_prep'].get('val_batch_size'))
        output_ids = self.model.run(
            self.trainer.session, dataset, sample, softmax_temperature, options=options) or []
        sequences = [self.output_encoding.decode(ids) for ids in output_ids]
        merged_sequences = []
        instrument_id = 0
        for seq, meta in zip(sequences, metadata_list):
            instrument_id += 1
            while meta['input_index'] > len(merged_sequences) - 1:
                merged_sequences.append(music_pb2.NoteSequence())
                instrument_id = 0

            # Apply features (instrument, velocity)
            if meta['note_features'] is not None:
                if self._cfg['output_encoding'].get('use_velocity', False):
                    # If the output has velocity information, do not override it
                    del meta['note_features']['velocity']

                set_note_fields(seq, **meta['note_features'], instrument=instrument_id)
            else:
                # If the style input had no notes, force the output to be empty
                seq.Clear()

            # Merge
            merged_sequences[-1].notes.extend(seq.notes)
            merged_sequences[-1].total_time = max(merged_sequences[-1].total_time, seq.total_time)
            instrument_info = merged_sequences[-1].instrument_infos.add()
            instrument_info.instrument = instrument_id
            instrument_info.name = meta['filter_name']

        return merged_sequences

    def _load_data(self, loader, training=False, encode=True, apply_filters=True,
                   metadata_list=None, normalize_velocity=False):
        max_target_len = self._cfg.get('max_target_length', np.inf)
        if apply_filters is False:
            filter_kwargs_dict = {'__all__': {}}
            filter_names = '__all__'
        elif apply_filters == '__program__':
            filter_kwargs_dict = None
        else:
            filter_kwargs_dict = self._cfg.get('style_note_filters')
            if apply_filters is not True:
                filter_kwargs_dict = {k: v for k, v in filter_kwargs_dict.items()
                                      if k in apply_filters}
            filter_names = sorted(filter_kwargs_dict.keys())

        def generator():
            i = 0
            long_skip_count = 0
            empty_count = 0
            for input_index, (src_seq, style_seq_all, tgt_seq_all) in enumerate(loader):
                if normalize_velocity:
                    src_seq, style_seq_all, tgt_seq_all = (
                        self._normalize_velocity(seq)
                        for seq in (src_seq, style_seq_all, tgt_seq_all))

                if apply_filters == '__program__':
                    # Create a filter for each program
                    programs = sorted(set((n.program, n.is_drum) for n in style_seq_all.notes))
                    filters = [
                        (f'program{p}' + ('d' if d else ''),
                         dict(programs=[p], drums=d))
                        for p, d in programs
                    ]
                else:
                    filters = [(name, filter_kwargs_dict[name]) for name in filter_names]

                for filter_name, filter_kwargs in filters:
                    tgt_seq = None
                    if tgt_seq_all is not None:
                        tgt_seq = music_pb2.NoteSequence()
                        tgt_seq.CopyFrom(tgt_seq_all)
                        filter_sequence(tgt_seq, **filter_kwargs)
                        if training and tgt_seq is not None and len(tgt_seq.notes) > max_target_len:
                            long_skip_count += 1
                            continue

                    style_seq = music_pb2.NoteSequence()
                    style_seq.CopyFrom(style_seq_all)
                    filter_sequence(style_seq, **filter_kwargs)

                    if training and (not src_seq.notes or not style_seq.notes):
                        empty_count += 1
                        continue

                    if metadata_list is not None:
                        metadata_entry = {
                            'input_index': input_index,
                            'src_filename': src_seq.filename,
                            'filter_name': filter_name,
                            'note_features': None
                        }
                        if len(style_seq.notes) > 0:
                            metadata_entry['note_features'] = {
                                'velocity': int(
                                    np.mean([n.velocity for n in style_seq.notes]) + .5),
                                'program': style_seq.notes[0].program,
                                'is_drum': style_seq.notes[0].is_drum
                            }
                        metadata_list.append(metadata_entry)

                    if encode:
                        src_encoded = self.input_encoding.encode(src_seq)
                        tgt_encoded = self.output_encoding.encode(
                            tgt_seq, add_start=True, add_end=True) if tgt_seq is not None else []
                        style_encoded = self.output_encoding.encode(style_seq)
                        yield src_encoded, style_encoded, tgt_encoded[:-1], tgt_encoded[1:]
                    else:
                        yield src_seq, style_seq, tgt_seq

                    i += 1

            if training:
                _LOGGER.info(f'Done loading data: {i} examples; '
                             f'skipped: {long_skip_count} too long, {empty_count} empty')

        return generator

    def _normalize_velocity(self, seq):
        if seq is None:
            return None
        if not self._cfg.get('normalize_velocity'):
            return seq

        seq_copy = music_pb2.NoteSequence()
        seq_copy.CopyFrom(seq)
        seq = seq_copy

        target_mean = self._cfg['normalize_velocity'].get('mean')
        target_std = np.sqrt(self._cfg['normalize_velocity'].get('variance'))
        velocities = np.fromiter((n.velocity for n in seq.notes if n.velocity), dtype=np.float32)
        mean = np.mean(velocities)
        std = np.std(velocities)

        for note in seq.notes:
            velocity = (note.velocity - mean) / (std + 1e-5) * target_std + target_mean
            velocity = np.rint(velocity).astype(np.int32)
            note.velocity = np.clip(velocity, 1, 127)

        return seq


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--logdir', type=str, required=True, help='model directory')
    parser.set_defaults(train_mode=False, sampling_seed=None)
    subparsers = parser.add_subparsers(title='action')

    subparser = subparsers.add_parser('train')
    subparser.set_defaults(func=Experiment.train, train_mode=True)

    subparser = subparsers.add_parser('run-midi')
    subparser.set_defaults(func=Experiment.run_midi)
    subparser.add_argument('source_file', metavar='INPUTFILE')
    subparser.add_argument('style_file', metavar='STYLEFILE')
    subparser.add_argument('output_file', metavar='OUTPUTFILE')
    subparser.add_argument('--checkpoint', default=None, type=str)
    subparser.add_argument('--batch-size', default=None, type=int)
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
    subparser.add_argument('--batch-size', default=None, type=int)
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
