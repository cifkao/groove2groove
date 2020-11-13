DATA_DIR=../../../data/synth/test
OUTPUT_DIR=.

set -e

for instr in Bass Guitar Piano Strings; do
  echo $instr >&2
  python -m groove2groove.eval.style_profiles \
    "$DATA_DIR/final/$instr.db" "$DATA_DIR/final/meta.json.gz" \
    --max-segments-per-style 60 --config config.yaml \
    >"$OUTPUT_DIR/$instr.json"
done

instr=Drums
echo $instr >&2
python -m groove2groove.eval.style_profiles \
  "$DATA_DIR/final/$instr.db" "$DATA_DIR/final/meta.json.gz" \
  --max-segments-per-style 60 --config config_drums.yaml \
  >"$OUTPUT_DIR/$instr.json"
