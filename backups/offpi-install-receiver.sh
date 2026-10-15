#!/bin/sh
# Run as bigly on the RECEIVING Pi from this folder: sh offpi-install-receiver.sh bigpi-001 'ssh-ed25519 AAAA... offpi-bigpi-001'
# The key may only write into ~/offpi-backups/FROM (rrsync -wo -no-del): it can't read, delete, or run commands.
set -eu
D="$(cd "$(dirname "$0")" && pwd)"; FROM=${1:?say which Pi sends}; AK=$HOME/.ssh/authorized_keys
if [ "${2:-}" = undo ]; then
  grep -v "offpi-backups/$FROM\"" "$AK" > "$AK.tmp" && cat "$AK.tmp" > "$AK" && rm -f "$AK.tmp"
  sudo -n systemctl disable --now offpi-prune.timer 2>/dev/null || true
  echo "undone on $(hostname): $FROM's key removed. Copies kept in ~/offpi-backups/$FROM (delete by hand if wanted)"; exit 0
fi
KEY=${2:?paste the key line}
case "$KEY" in *[\"\\\']*|*"
"*) echo "STOP: that key line has odd characters. Nothing changed." >&2; exit 1 ;; esac
case "$KEY" in "ssh-ed25519 "*" offpi-"*) ;; *) echo "STOP: that doesn't look like an offpi key line. Nothing changed." >&2; exit 1 ;; esac
command -v rrsync >/dev/null && command -v python3 >/dev/null || { echo "STOP: rrsync or python3 missing. Nothing changed." >&2; exit 1; }
grep -q "offpi-backups/$FROM\"" "$AK" && { echo "STOP: a key for $FROM is already there. Nothing changed." >&2; exit 1; }
install -d -m 700 "$HOME/offpi-backups" "$HOME/offpi-backups/$FROM"
cp -p "$AK" "$AK.before-offpi-$(date +%F)"
echo "command=\"$(command -v rrsync) -wo -no-del -munge $HOME/offpi-backups/$FROM\",restrict $KEY" >> "$AK"
sudo -n install -m 755 "$D/offpi-prune.sh" /usr/local/bin/offpi-prune.sh
sudo -n install -m 644 "$D/offpi-prune.service" "$D/offpi-prune.timer" /etc/systemd/system/
sudo -n systemctl daemon-reload; sudo -n systemctl enable --now offpi-prune.timer
echo "ok: $(hostname) will accept $FROM's copies into ~/offpi-backups/$FROM; backup of keys: $AK.before-offpi-$(date +%F)"
