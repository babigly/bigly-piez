#!/bin/sh
# Run on a Pi the page can restart (BigPi-001, AnchorPi, Marketing, Fulfillment), from a folder holding the new piez-remote.
# Adds read-only "which apps are running" lines to the health word. Undo: sh services-install-pi.sh undo
set -eu
D="$(cd "$(dirname "$0")" && pwd)"; T=/usr/local/bin/piez-remote; B=$T.before-services-2026-10-15
if [ "${1:-}" = undo ]; then sudo -n install -o root -g root -m 755 "$B" "$T"; echo "undone on $(hostname)"; exit 0; fi
[ "$(sha256sum "$T" | cut -c1-8)" = 87c35ee4 ] || { echo "STOP: $T on $(hostname) isn't the expected version. Nothing changed." >&2; exit 1; }
sudo -n cp -p "$T" "$B"
sudo -n install -o root -g root -m 755 "$D/piez-remote" "$T"
if SSH_ORIGINAL_COMMAND=health "$T" | grep -q '^ports=[0-9]'; then echo "ok: $(hostname) reports its apps; backup $B"
else echo "FAILED: no app list on $(hostname); run: sh services-install-pi.sh undo" >&2; exit 1; fi
