# bigly-piez

Bigly Piez: the control center for the Bigly Raspberry Pis ("Pi pets").

- `health/` — the dashboard page (live at https://bigpi-002.tail6c7763.ts.net:8450/) and its restart helper in `health/power/`. Install steps: `health/INSTALL-HEALTH.md`.
- `backups/` — nightly copies of each BigPi's backups onto the other BigPi, so one dead SD card doesn't lose any data. Install steps: `backups/INSTALL-BACKUPS.md`.
- `.github/workflows/notify-slack.yml` — posts a 🥧 alert in the shared Slack channel each time something is published to `main`.

Pi list and open items live in `babigly/bigly-notes` (`PIS.md`, `projects/bigly-piez.md`).
