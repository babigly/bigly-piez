# Off-Pi backup copies (BigPi-001 ⇄ BigPi-002)

_Built 2026-10-15 after the audit found every backup sits on the same SD card as its app. Nothing here is installed until BA types the go-ahead. Every step has an undo._

## What it does

- **Every night at 04:45**, BigPi-001 copies its backup folders to BigPi-002, and BigPi-002 copies DevHub's backups to BigPi-001, over Tailscale with `rsync`.
- It only **adds** files. It never deletes anything on the sending Pi, and the copy key **can't delete, read or run anything** on the receiving Pi: the receiver locks it to `rrsync -wo -no-del` inside one folder.
- **Once a week** the receiving Pi tidies its copies: it always keeps the newest 14 files in each folder and only removes older ones once they're past 30 days. If the sender goes quiet, the last copies stay put.
- BiglyCraft's hourly saves are skipped (only its daily and pre-update saves are copied) to keep the size small.

| From | Folder | Lands on | Size today |
|---|---|---|---|
| BigPi-001 | `~/biglybank-backups` | BigPi-002 `~/offpi-backups/bigpi-001/biglybank` | 1.2 MB |
| BigPi-001 | `~/biglydex-v2/backups` | … `/biglydex-v2` | 145 MB |
| BigPi-001 | `~/biglycraft-data/backups` (no hourlies) | … `/biglycraft` | ~110 MB |
| BigPi-001 | `~/bigly-games/data/backups` | … `/bigly-games` | 0.4 MB |
| BigPi-002 | `/var/lib/devhub/backups` | BigPi-001 `~/offpi-backups/bigpi-002/devhub` | 2 MB |

BigPi-002 has 23 GB free and BigPi-001 has 101 GB free, so after 30 days this is well under 1 GB on each.

## Files

| File | Goes where |
|---|---|
| `offpi-send.sh`, `offpi-send.service`, `offpi-send.timer` | Each sending Pi (by `offpi-install-sender.sh`) |
| `send.conf.bigpi-001`, `send.conf.bigpi-002` | Sender settings: target, key path, folders. No secrets |
| `offpi-prune.sh`, `offpi-prune.service`, `offpi-prune.timer` | Each receiving Pi (by `offpi-install-receiver.sh`) |

## Steps (from BA's PC, in a copy of this folder)

**1. Copy the folder to both Pis**

```
scp -r . bigly@100.105.184.68:/tmp/offpi/
scp -r . bigly@bigpi-002.tail6c7763.ts.net:/tmp/offpi/
```

**2. Make each sender** (prints a key line; nothing runs on a timer yet)

```
ssh bigly@100.105.184.68 "sudo sh /tmp/offpi/offpi-install-sender.sh send.conf.bigpi-001"
ssh bigly@bigpi-002.tail6c7763.ts.net "sudo sh /tmp/offpi/offpi-install-sender.sh send.conf.bigpi-002"
```

**3. Let each receiver accept the other's key** (paste the key line from step 2)

```
ssh bigly@bigpi-002.tail6c7763.ts.net "sh /tmp/offpi/offpi-install-receiver.sh bigpi-001 'KEY LINE FROM BIGPI-001'"
ssh bigly@100.105.184.68 "sh /tmp/offpi/offpi-install-receiver.sh bigpi-002 'KEY LINE FROM BIGPI-002'"
```

**4. Test once by hand, then turn the timers on**

```
ssh bigly@100.105.184.68 "sudo systemctl start offpi-send.service; systemctl status offpi-send.service --no-pager | tail -8"
ssh bigly@bigpi-002.tail6c7763.ts.net "sudo systemctl start offpi-send.service; systemctl status offpi-send.service --no-pager | tail -8"
```

Each folder should say `ok NAME`. Then check the copies landed (`du -sh ~/offpi-backups/*/*` on each Pi), and only then:

```
ssh bigly@100.105.184.68 "sudo systemctl enable --now offpi-send.timer"
ssh bigly@bigpi-002.tail6c7763.ts.net "sudo systemctl enable --now offpi-send.timer"
```

## Getting a backup back

If BigPi-001's card dies, its newest backups are on BigPi-002 in `~/offpi-backups/bigpi-001/`. Copy the one you need onto the rebuilt Pi and restore it with that app's own restore steps (the bank and Biglypedia files are `pg_dump` files, BiglyCraft's are SQLite files). For DevHub, copy a `devhub-STAMP` folder from BigPi-001 back to `/var/lib/devhub/backups/` and restore it with DevHub's own tools. These restore steps weren't tried yet.

## Undo

- Each sender: `sudo sh /tmp/offpi/offpi-install-sender.sh undo` (stops the timer, removes the key, units and settings).
- Each receiver: `sh /tmp/offpi/offpi-install-receiver.sh bigpi-001 undo` on BigPi-002, `… bigpi-002 undo` on BigPi-001 (removes the key line, stops the tidy timer). A copy of the old key list is kept as `~/.ssh/authorized_keys.before-offpi-DATE`. The copies in `~/offpi-backups` are kept until you delete them.

## How it was tested (in the cloud, not on a Pi)

- Sent pretend backup folders through the real `rrsync -wo -no-del -munge` lock: files arrive; hourlies are skipped; a missing folder is reported and the run fails (so the service shows as failed); a smaller source never removes copies.
- The lock refuses reading back, `--delete`, and `..` paths.
- Tidy: with 22 files it keeps the newest 14 and removes only the ones past 30 days; with 5 files all 90 days old it keeps all 5.
- Ran both install scripts with their undo: the sender picks `root` only when it can't read a folder as `bigly` (DevHub on BigPi-002), its key is mode 600, and running it twice stops safely. The receiver refuses a second key for the same Pi and refuses key lines that aren't from this setup or have odd characters.
- **Not tested on the real Pis yet.** Also not done: a real restore drill.

## Limits

- Both Pis are in the same building, so this doesn't help in a fire, flood or theft. A later step could have BA's PC collect the copies too.
- Bank, Biglypedia and BiglyCraft copies aren't encrypted, same as the originals. They sit on BigPi-002, which is tailnet-only and has no public apps.
- The copy key can't delete, but it could overwrite a copy that has the same file name. Backup names carry a timestamp, so normal runs never do that.
- A failed nightly copy shows as a failed service on the Pi; the dashboard doesn't show it yet.
