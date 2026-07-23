---
name: sonycam
description: >-
  Control Sony Alpha cameras over USB PC Remote with sonycam: connect, ISO/shutter/aperture,
  in-camera movie REC, liveview with red REC tally, and CFexpress/SD pull. Use when recording
  A-roll, operating an A1/A7/FX body from the Mac, teleprompter camera control, or pulling clips.
---

# sonycam — Alpha camera control

CLI-first control for Sony Alpha bodies via the local Alpha Camera REST API.
Verified on **ILCE-1M2 (A1 II)**. Pair with `screcord` for screen capture — this is **not** a screen recorder.

## Resolve binary

```bash
command -v sonycam || echo "$HOME/.local/bin/sonycam"
# from repo: source .venv/bin/activate && sonycam
```

## Preconditions (don’t skip)

1. Camera powered on
2. USB mode = **PC Remote** (not Mass Storage / Auto)
3. USB cable connected
4. `@alpha-sdk/api` installed (`npm install -g @alpha-sdk/api`) and Sony CRSDK license accepted once

## Session checklist

```
- [ ] sonycam server start
- [ ] sonycam connect
- [ ] sonycam status          # connected=True, movie mode, exposure OK
- [ ] sonycam set --iso … --shutter …
- [ ] (optional) sonycam liveview
- [ ] sonycam rec start  → talent → sonycam rec stop
- [ ] sonycam pull --latest --out ~/Movies/sonycam
```

## Standard commands

```bash
sonycam server start
sonycam connect
sonycam status
sonycam status --json

sonycam set --iso 800 --shutter 1/200
sonycam set --aperture 2.8

sonycam liveview                 # red border while REC (blocks)
sonycam rec start
sonycam rec stop
sonycam rec status

sonycam pull --list
sonycam pull --latest --out ~/Movies/sonycam
```

## Hard rules

1. **Master = in-camera.** Liveview JPEGs are monitoring only — never the edit master.
2. Prefer `rec start` / `rec stop` over `toggle` (idempotent via `recording-state`).
3. If disconnected → `sonycam connect` (`remote-transfer` + `pc-remote` priority).
4. Body must be in a **movie** exposure mode or REC will stay Not Recording.
5. Agents: prefer `--json` on `status` / `pull --list`.
6. Do **not** use gphoto2 `--capture-movie` as the master path.

## Failure checklist

| Symptom | Fix |
|---------|-----|
| Cannot reach API | `sonycam server start` |
| Port open, no response | `sonycam server stop && sonycam server start` |
| CameraWebApp dyld / OpenSSL | `sonycam server start` refreshes Homebrew openssl shim |
| No cameras | PC Remote + replug USB; quit Creators’ App if it holds the device |
| Property / REC fails | `connect` then retry; confirm movie mode |
| Pull empty / wrong clip | `--slot 1` (or 2); use `--list` before `--latest` |

## With screcord (YouTube A-roll + screen)

```bash
# Terminal A — camera monitor
sonycam liveview

# Terminal B — screen
screcord record --preset tutorial --slug topic --display main

# Camera master still via sonycam rec start/stop + pull
```

## Reference

- Flags + API map: [reference.md](reference.md)
