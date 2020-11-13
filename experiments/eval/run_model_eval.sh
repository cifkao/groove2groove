#!/bin/bash
logdir=$1
[[ -n "$logdir" ]] || { echo "No logdir given" >&2; exit 1; }

style_fname=all_except_drums.db
if [[ $(basename "$logdir") =~ drums ]]; then
  style_fname=all.db
fi

set -x

mkdir -p $logdir/out
rm -f $logdir/out/{test,bodh}_{sample06,greedy}.db

# Synthetic test set, sampling mode
python -m groove2groove.models.roll2seq_style_transfer --logdir "$logdir" run-test \
    --sample --softmax-temperature 0.6 --seed 1234 --batch-size 128 \
    --filters training \
    ../../data/synth/test/final/all_except_drums.db \
    ../../data/synth/test/final/$style_fname \
    pairs_test.tsv \
    "$logdir/out/test_sample06.db"

# Synthetic test set, greedy mode
python -m groove2groove.models.roll2seq_style_transfer --logdir "$logdir" run-test \
    --batch-size 128 \
    --filters training \
    ../../data/synth/test/final/all_except_drums.db \
    ../../data/synth/test/final/$style_fname \
    pairs_test.tsv \
    "$logdir/out/test_greedy.db"

# Bodhidharma, sampling mode
python -m groove2groove.models.roll2seq_style_transfer --logdir "$logdir" run-test \
    --sample --softmax-temperature 0.6 --seed 1234 --batch-size 128 \
    ../../data/bodhidharma/final/vel_norm_biab/all_except_drums.db \
    ../../data/bodhidharma/final/vel_norm_biab/$style_fname \
    pairs_bodh.tsv \
    "$logdir/out/bodh_sample06.db"

# Bodhidharma, greedy mode
python -m groove2groove.models.roll2seq_style_transfer --logdir "$logdir" run-test \
    --batch-size 128 \
    ../../data/bodhidharma/final/vel_norm_biab/all_except_drums.db \
    ../../data/bodhidharma/final/vel_norm_biab/$style_fname \
    pairs_bodh.tsv \
    "$logdir/out/bodh_greedy.db"
