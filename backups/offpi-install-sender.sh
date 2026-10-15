#!/bin/sh
# Run with sudo on the SENDING Pi from this folder: sudo sh offpi-install-sender.sh send.conf.bigpi-001
# Makes a new key that the other Pi will only let drop files into one folder. Undo: sudo sh offpi-install-sender.sh undo
set -eu
D="$(cd "$(dirname "$0")" && pwd)"; E=/etc/bigly-offpi
if [ "${1:-}" = undo ]; then
  systemctl disable --now offpi-send.timer 2>/dev/null || true
  rm -rf /etc/systemd/system/offpi-send.service /etc/systemd/system/offpi-send.timer /etc/systemd/system/offpi-send.service.d \
    /usr/local/bin/offpi-send.sh "$E"
  systemctl daemon-reload; echo "undone on $(hostname): sender removed"; exit 0
fi
[ -f "$D/${1:?say which send.conf}" ] || { echo "STOP: $1 not found. Nothing changed." >&2; exit 1; }
command -v rsync >/dev/null || { echo "STOP: rsync isn't installed. Nothing changed." >&2; exit 1; }
[ -e "$E" ] && { echo "STOP: $E already exists. Run undo first. Nothing changed." >&2; exit 1; }
. "$D/$1"
# DevHub's backups belong to the devhub user, so the BigPi-002 copy has to read them as root.
RUNAS=bigly; for pair in $FOLDERS; do sudo -u bigly test -r "${pair#*=}" || RUNAS=root; done
install -d -m 700 -o "$RUNAS" "$E"
install -m 644 "$D/$1" "$E/send.conf"
ssh-keygen -q -t ed25519 -N "" -C "offpi-$(hostname)" -f "$E/id_ed25519"
ssh-keyscan -t ed25519 "${TARGET#*@}" > "$E/known_hosts" 2>/dev/null
[ -s "$E/known_hosts" ] || { echo "STOP: couldn't reach ${TARGET#*@}. Run undo, then try again." >&2; exit 1; }
chown -R "$RUNAS" "$E"
install -m 755 "$D/offpi-send.sh" /usr/local/bin/offpi-send.sh
install -m 644 "$D/offpi-send.service" "$D/offpi-send.timer" /etc/systemd/system/
if [ "$RUNAS" = root ]; then mkdir -p /etc/systemd/system/offpi-send.service.d; printf '[Service]\nUser=root\n' > /etc/systemd/system/offpi-send.service.d/user.conf; fi
systemctl daemon-reload
echo "ok: sender ready on $(hostname) (runs as $RUNAS, timer NOT on yet). Give the other Pi this key line:"
cat "$E/id_ed25519.pub"
