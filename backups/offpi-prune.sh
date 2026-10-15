#!/bin/sh
# Runs on the receiving Pi. In each copied folder it always keeps the newest KEEP files,
# and removes older ones only once they are past DAYS old, so a silent sender never empties it.
set -eu
ROOT=${OFFPI_ROOT:-/home/bigly/offpi-backups}; KEEP=${OFFPI_KEEP:-14}; DAYS=${OFFPI_DAYS:-30}
cutoff=$(( $(date +%s) - DAYS * 86400 ))
for dir in "$ROOT"/*/*/; do
  [ -d "$dir" ] || continue
  find "$dir" -type f -printf '%T@ %p\n' | sort -rn | tail -n +"$((KEEP + 1))" |
  while read -r t path; do
    if [ "${t%.*}" -lt "$cutoff" ]; then rm -f -- "$path"; echo "pruned $path"; fi
  done
done
find "$ROOT" -mindepth 3 -type d -empty -delete
echo "ok: pruned $ROOT (keep newest $KEEP, older than $DAYS days go)"
