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
