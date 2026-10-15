#!/bin/sh
# Run on BigPi-002 as bigly to put back the helper and page from before the services update.
set -eu
H=/home/bigly/piez-restart; P=/home/bigly/pi-pets; B=before-services-2026-10-15
cp -p "$H/restart.py.$B" "$H/restart.py"; cp -p "$H/piez-remote.$B" "$H/piez-remote"; cp -p "$P/index.$B.html" "$P/index.html"
sudo -n systemctl restart piez-restart
echo "undone: service $(systemctl is-active piez-restart)"
