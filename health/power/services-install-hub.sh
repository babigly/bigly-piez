#!/bin/sh
# Run on BigPi-002 as bigly from a folder holding the new restart.py, piez-remote and index.html.
# Stops if the live files aren't the versions this update was built on; backs everything up before copying.
set -eu
D="$(cd "$(dirname "$0")" && pwd)"; H=/home/bigly/piez-restart; P=/home/bigly/pi-pets; B=before-services-2026-10-15
check() { [ "$(sha256sum "$1" | cut -c1-8)" = "$2" ] || { echo "STOP: $1 is not the version this update expects ($2). Nothing changed." >&2; exit 1; }; }
check "$H/restart.py" af51f4b7
check "$H/piez-remote" 87c35ee4
check "$P/index.html" f1d0859b
cp -p "$H/restart.py" "$H/restart.py.$B"; cp -p "$H/piez-remote" "$H/piez-remote.$B"; cp -p "$P/index.html" "$P/index.$B.html"
install -m 644 "$D/restart.py" "$H/restart.py"; install -m 755 "$D/piez-remote" "$H/piez-remote"
sudo -n systemctl restart piez-restart; sleep 3
echo "service: $(systemctl is-active piez-restart)"
curl -sf --max-time 90 http://127.0.0.1:8452/health || { echo "STOP: health check failed; undo with services-undo-hub.sh" >&2; exit 1; }
echo
install -m 644 "$D/index.html" "$P/index.html"
echo "ok: helper and page updated; backups end in .$B"
