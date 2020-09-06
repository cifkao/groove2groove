#!/bin/bash
archive_name=groove2groove-data-v1.0.0
archive=$archive_name.tar.gz
download_url="https://zenodo.org/record/3958000/files/$archive?download=1"
checksum=c407de7b3676267660c88dc6ee351c79

set -e

if [[ ! -e "$archive" ]]; then
  wget "$download_url" -O $archive
else
  echo "File $archive already exists, skipping download" >&2
fi
md5sum --check <(printf '%s\t%s\n' $checksum $archive)

for dir in {train,val,test}/fixed; do
  if [[ -e "$dir" ]]; then
    echo "Removing $dir" >&2
    rm -rf "$dir"
  fi
  echo "Extracting $dir" >&2
  tar xzf $archive --strip-components 2 --no-overwrite-dir $archive_name/midi/$dir
done
