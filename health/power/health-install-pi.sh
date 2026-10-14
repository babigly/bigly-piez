#!/bin/sh
# Run on a Pi the page can restart (BigPi-001, AnchorPi, Marketing, Fulfillment), from a folder holding the new piez-remote.
# Gives the restart key one extra read-only word, "health". Undo: sh health-install-pi.sh undo
set -eu
D="$(cd "$(dirname "$0")" && pwd)"; T=/usr/local/bin/piez-remote; B=$T.before-health-2026-10-14
if [ "${1:-}" = undo ]; then sudo -n install -o root -g root -m 755 "$B" "$T"; echo "undone on $(hostname)"; exit 0; fi
[ "$(sha256sum "$T" | cut -c1-8)" = 424c3eb0 ] || { echo "STOP: $T on $(hostname) isn't the expected version. Nothing changed." >&2; exit 1; }
sudo -n cp -p "$T" "$B"
sudo -n install -o root -g root -m 755 "$D/piez-remote" "$T"
if SSH_ORIGINAL_COMMAND=health "$T" | grep -q '^disk=[0-9]'; then echo "ok: $(hostname) can report health; backup $B"
else echo "FAILED: health didn't answer on $(hostname); run: sh health-install-pi.sh undo" >&2; exit 1; fi
