#!/bin/sh
# Copies this Pi's backup folders to the other BigPi over Tailscale. Never deletes anything on either side.
# Settings: /etc/bigly-offpi/send.conf (TARGET, KEY, FOLDERS, EXCLUDE). Exits 1 if any folder failed.
set -eu
CONF=${OFFPI_CONF:-/etc/bigly-offpi/send.conf}
. "$CONF"
SSH=${OFFPI_SSH:-ssh -i $KEY -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$(dirname "$CONF")/known_hosts}
failed=0
for pair in $FOLDERS; do
  name=${pair%%=*}; src=${pair#*=}
  if [ ! -d "$src" ]; then echo "SKIP $name: $src is missing" >&2; failed=1; continue; fi
  set -f; ex=""; for p in ${EXCLUDE:-}; do ex="$ex --exclude=$p"; done; set +f
  # shellcheck disable=SC2086
  if rsync -rlt --no-owner --no-group --chmod=Du=rwx,Dgo=,Fu=rw,Fgo= --timeout=300 $ex -e "$SSH" "$src/" "$TARGET:$name/"; then
    echo "ok $name: $(find "$src" -type f | wc -l) files checked"
  else
    echo "FAILED $name" >&2; failed=1
  fi
done
exit $failed
