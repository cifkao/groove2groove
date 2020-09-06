#!/bin/bash
# Run this script to prepare the Bodhidharma data in the current directory.
# Will download the dataset first.

shopt -s extglob
set -o pipefail
trap "exit 1" INT

src_dir=MIDI_Files

function die { [[ $# > 0 ]] || set -- Failed.; echo; echo >&2 "$@"; exit 1; }
function log { echo >&2 "$@"; }
function log_progress { echo -en "\r\033[2K$@ "; }

tmp_dir=$(mktemp -d)
function cleanup { rm -rf "$tmp_dir"; }
trap cleanup EXIT


if [[ ! -e "$src_dir" ]]; then
  wget http://www.music.mcgill.ca/~cmckay/protected/Bodhidharma_MIDI.zip || die
  unzip -n Bodhidharma_MIDI.zip || die
  rm -f Bodhidharma_MIDI.zip
fi
[[ -e "$src_dir" ]] || die "$src_dir does not exist"

# Fix the key signatures and filenames
dir=01_fixed
mkdir "$dir" && {
  log "Found $(find -L "$src_dir" -type f | wc -l) files in $src_dir"
  find -L "$src_dir" | grep -Ei '\.mid$' | while read -r f; do
    fname="$(basename "$f" | sed -r 's/\.mid/.mid/i')"
    log_progress "$fname"
    python -m groove2groove.scripts.fix_midi_key_signatures "$f" "$dir/$fname"
  done || die
  log
  log "Created $(find "$dir" -name '*.mid' | wc -l) files in $dir"
}

# Filter the files to have 4/4 time only
dir=02_filtered
mkdir "$dir" && {
  python -m groove2groove.scripts.filter_4beats 01_fixed/*.mid | while read -r f; do
    log_progress "$(basename "$f")"
    ln "$f" "$dir/$(basename "$f")" || die
  done || die
  log
  log "Linked $(find "$dir" -name '*.mid' | wc -l) files to $dir"
}

# Chop the files into 8-bar segments, save as NoteSequences
dir=03_chopped
mkdir "$dir" && {
  python -m groove2groove.scripts.chop_midi \
      --bars-per-segment 8 \
      --min-notes-per-segment 1 \
      --merge-instruments \
      --force-tempo 60 \
      02_filtered/ "$dir/data" || die
}

# Separate the instrument tracks
dir=04_separated
mkdir "$dir" && {
  instr=all_except_drums
    python -m groove2groove.scripts.filter_note_sequences \
    --no-drums \
    03_chopped/data.tfrecord "$dir/$instr.tfrecord" || die

  ln 03_chopped/data.tfrecord "$dir/all.tfrecord" || die
}

# Make an LMDB database
dir=05_db
mkdir "$dir" && {
  for recordfile in 04_separated/*.tfrecord; do
    prefix=$(basename "${recordfile%.tfrecord}")
    python -m groove2groove.scripts.tfrecord_to_lmdb "$recordfile" "$tmp_dir/$prefix.db" || die
    rm -f "$tmp_dir/$prefix".db-lock
    mv -v -t "$dir" "$tmp_dir/$prefix"* || die
  done
}

dir=final
mkdir "$dir" && {
  ln -t "$dir" 04_separated/* 05_db/*

  # Turn the metadata into a dict, add more information.
  zcat 03_chopped/data_meta.json.gz | python -c '
import json, sys, os, csv

with open("recordings_key.tsv") as f:
  bodh_meta = {}
  for filename, song_name, artist, genre in csv.reader(f, delimiter="\t"):
    bodh_meta[os.path.splitext(filename)[0] + ".mid"] = {
      "song_name": song_name,
      "artist": artist,
      "genre": genre
    }

data = json.load(sys.stdin)
data_dict = {}
key_len = len(str(len(data) - 1))
for i, item in enumerate(data):
    item.update(bodh_meta[item["filename"]])
    key = str(i).zfill(key_len)
    data_dict[key] = item
json.dump(data_dict, sys.stdout, separators=(",", ":"))
    ' | gzip -c >"$dir/meta.json.gz"
}

log Done.

exit 0
