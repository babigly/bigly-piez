# Bigly Piez: live health numbers

_Built 2026-10-14. Nothing here is installed until BA says so. Every step backs up first and has an undo._

## What it does

Every 2 minutes BigPi-002 asks each Pi for 5 numbers: temperature, how busy the CPU is, how full memory is, how full the disk is, and how long it has been on. Each pet's card shows them, and the pet's face uses the real temperature and disk.

- It reuses the locked-down Restart key. That key can now say one more word, `health`, which only **reads** numbers. It still can't run anything else.
- No new app, port or service. The restart helper just gets a new `/api/health` page.
- A Pi that hasn't had its update yet keeps its sample numbers and says "needs the health update".
- Cust. Service and Signage stay switched off, same as the Restart buttons.

## Files

| File | Goes where |
| --- | --- |
| `power/piez-remote` | Each Pi: `/usr/local/bin/piez-remote`. BigPi-002: `~/piez-restart/piez-remote` |
| `power/restart.py` | BigPi-002: `~/piez-restart/restart.py` |
| `index.html` | BigPi-002: `~/pi-pets/index.html` |
| `power/health-install-pi.sh` | Runs once on BigPi-001, AnchorPi, Marketing, Fulfillment |
| `power/health-install-hub.sh` / `health-undo-hub.sh` | Run once on BigPi-002 |

Both install scripts **stop without changing anything** if the file on the Pi isn't the exact version this was built on.

## Steps (from BA's PC, in `C:\CLAUDE\pi-pets\health`, a copy of this folder)

Order doesn't matter. Pis updated before BigPi-002 just wait; BigPi-002 updated first shows "needs the health update" for the others.

**1. The four Pis** (one at a time; each line copies two files, then runs the script):

```
scp power/piez-remote power/health-install-pi.sh bigly@100.105.184.68:/tmp/
ssh bigly@100.105.184.68 "sh /tmp/health-install-pi.sh"

scp power/piez-remote power/health-install-pi.sh biglymotors@100.91.185.97:/tmp/
ssh biglymotors@100.91.185.97 "sh /tmp/health-install-pi.sh"

scp -J biglymotors@100.91.185.97 power/piez-remote power/health-install-pi.sh jukebox@192.168.3.182:/tmp/
ssh -J biglymotors@100.91.185.97 jukebox@192.168.3.182 "sh /tmp/health-install-pi.sh"

scp -J biglymotors@100.91.185.97 power/piez-remote power/health-install-pi.sh jukebox@192.168.2.84:/tmp/
ssh -J biglymotors@100.91.185.97 jukebox@192.168.2.84 "sh /tmp/health-install-pi.sh"
```

Each should end with `ok: <name> can report health`.

**2. BigPi-002:**

```
scp power/restart.py power/piez-remote index.html power/health-install-hub.sh power/health-undo-hub.sh bigly@bigpi-002.tail6c7763.ts.net:/tmp/
ssh bigly@bigpi-002.tail6c7763.ts.net "mkdir -p ~/piez-health && cp /tmp/restart.py /tmp/piez-remote /tmp/index.html /tmp/health-*.sh ~/piez-health/ && sh ~/piez-health/health-install-hub.sh"
```

It should print the live numbers and `ok: helper and page updated`.

**3. Check:** open https://bigpi-002.tail6c7763.ts.net:8450/, tap a pet, and look for "Live numbers at …" under its name. Then on BigPi-002 run `sh ~/piez-restart/piez-check.sh`: every Pi should still say `check-in ok, other commands refused`.

## Undo

- BigPi-002: `sh ~/piez-health/health-undo-hub.sh`
- Each Pi: `sh /tmp/health-install-pi.sh undo` (or copy `/usr/local/bin/piez-remote.before-health-2026-10-14` back with sudo)

## How it was tested (in the cloud, not on a Pi)

- `python3 -m unittest test_restart.py` in `power/`: 9 tests pass (number parsing, junk input gives blanks not guesses, the key still refuses `id`, `health; id`, `health && reboot`, the `/health` page, and "needs the health update").
- Ran the helper with pretend Pis and the real page in a headless browser on desktop and phone sizes, light and dark: live numbers show, unknown temperature shows "?", no page errors.
- Ran both install scripts against a pretend `/home/bigly`: install, undo, and the "wrong version, stop" check all work.
- **Not tested on a real Pi yet.** The temperature file (`/sys/class/thermal/thermal_zone0/temp`) is standard on Raspberry Pi OS but wasn't checked on each Pi; if one lacks it, that pet just shows "Temp ?".
- The live copies on BigPi-002 and the Pis weren't read; the install scripts' version check covers that.

---

# Update 2026-10-15: real app lights

_Nothing here is installed until BA types the go-ahead. Same pattern as above: version check, backup, undo._

**What changes:** the `health` word also lists which TCP ports are listening and which services are running or failed (names only, read-only). Each app on a pet's card turns **Up** or **Down** from that, instead of always showing "Up". If a Pi hasn't sent the list yet, or an app has no check (AnchorForge), it says **Not checked** in grey. A failed service shows as its own red line and makes the pet look sick. The 3 stale to-dos (Active Cooler, Fulfillment route fix, Move BNN) are gone, and BigPi-001's card now also lists BiglyCraft, the Biglympics watch page and Docker.

| App | Counts as up when |
|---|---|
| AnchorPi | Jukebox port 8080, MPD 6600–6603, room streams 18001–18003, Caddy 80 |
| BigPi-001 | Biglypedia 8470+8471, bank 8790, games 4173, signage 8095, BiglyCraft 8800, Postgres 5432, `bigly-games-watch` and `docker` running; Portal 8090/8091 is expected off |
| BigPi-002 | DevHub 8640, restart helper 8452, `docker` running |
| Marketing, Fulfillment | a running service whose name starts with `bigly-room` |

**Steps** (from `C:\CLAUDE\pi-pets\health`, a copy of this folder):

1. The four Pis, one at a time (same hosts as above):
   `scp power/piez-remote power/services-install-pi.sh HOST:/tmp/` then `ssh HOST "sh /tmp/services-install-pi.sh"`. Each should end with `ok: NAME reports its apps`.
2. BigPi-002: copy `power/restart.py power/piez-remote index.html power/services-install-hub.sh power/services-undo-hub.sh` into `~/piez-services/` and run `sh ~/piez-services/services-install-hub.sh`.
3. Check: `curl -s http://127.0.0.1:8452/health` on BigPi-002 shows `ports` and `running` for every Pi. Open the dashboard and make sure every app that's really running says **Up**. If the room players say Down, their service has a different name; undo or adjust before calling it done.

**Undo:** BigPi-002 `sh ~/piez-services/services-undo-hub.sh`; each Pi `sh /tmp/services-install-pi.sh undo`.

**Tested in the cloud:** 11 unit tests (new: ports/services parse, odd names give blanks, the key still refuses everything else); the page with pretend live data in a headless browser (Up, Down, Not checked, Off on purpose, a failed service, a Pi on the old script, "Preview a bad day"), no page errors; the hub install script against a pretend home (install, refuses to run twice, undo restores the exact old files). **Not tested on the real Pis yet.**
