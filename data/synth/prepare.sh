#!/bin/bash
shopt -s extglob
set -o pipefail
trap "exit 1" INT


function die { [[ $# > 0 ]] || set -- Failed.; echo; echo >&2 "$@"; exit 1; }
function log { echo >&2 "$@"; }
function log_progress { echo -en "\r\033[2K$@ "; }

[[ "$#" -eq 1 ]] || die 'Expected exactly one argument: the working directory'
cd "$1"

tmp_dir=$(mktemp -d)
function cleanup { rm -rf "$tmp_dir"; }
trap cleanup EXIT

data_dir=fixed
[[ -d $data_dir ]] || die "$data_dir does not exist"

log "Preparing data in $PWD"

dir=02_chopped
mkdir "$dir" && {
  python -m groove2groove.scripts.chop_midi \
      --bars-per-segment 8 \
      --skip-bars 2 \
      --min-notes-per-segment 1 \
      --merge-instruments \
      --force-tempo 60 \
      "$data_dir/" "$dir/data" || die
}

dir=03_separated
mkdir "$dir" && {
  for instr in Bass Piano Guitar Strings Drums; do
    python -m groove2groove.scripts.filter_note_sequences \
        --instrument-re "^BB $instr\$" \
        02_chopped/data.tfrecord "$dir/$instr.tfrecord" || die
  done

  python -m groove2groove.scripts.filter_note_sequences --no-drums \
      02_chopped/data.tfrecord "$dir/all_except_drums.tfrecord" || die

  ln 02_chopped/data.tfrecord "$dir/all.tfrecord" || die
}

dir=04_db
mkdir "$dir" && {
  for recordfile in 03_separated/*.tfrecord; do
    prefix=$(basename "${recordfile%.tfrecord}")
    python -m groove2groove.scripts.tfrecord_to_lmdb "$recordfile" "$tmp_dir/$prefix.db" || die
    rm -f "$tmp_dir/$prefix".db-lock
    mv -v -t "$dir" "$tmp_dir/$prefix"* || die
  done
}

dir=final
mkdir "$dir" && {
  ln -t "$dir" 03_separated/* 04_db/*

  # Add keys, song names and styles to the metadata.
  zcat 02_chopped/data_meta.json.gz | python3 -c '
import json, sys
data = json.load(sys.stdin)
data_dict = {}
key_len = len(str(len(data) - 1))
for i, item in enumerate(data):
    item["song_name"], item["style"], _ = item["filename"].rsplit(".", maxsplit=2)
    key = str(i).zfill(key_len)
    data_dict[key] = item
json.dump(data_dict, sys.stdout, separators=(",", ":"))
    ' | gzip -c >"$dir/meta.json.gz"


  # Shuffle the data.
  mkdir "$dir/shuf"
  paste <(python -m groove2groove.scripts.list_lmdb_keys "$dir/all.db" | shuf) \
        <(python -m groove2groove.scripts.list_lmdb_keys "$dir/all.db" | sort) >"$dir/shuf/key_map" || die
  for instr in Bass Piano Guitar Strings Drums all all_except_drums; do
    log_progress $instr
    python -m groove2groove.scripts.permute_lmdb "$dir/$instr.db" "$dir/shuf/$instr.db" "$dir/shuf/key_map" || die
  done
  python -m groove2groove.scripts.permute_json_map "$dir/meta.json.gz" "$dir/shuf/meta.json.gz" "$dir/shuf/key_map" || die
}

log Done.

exit 0
