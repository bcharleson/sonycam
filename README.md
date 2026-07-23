# sonycam

Agent-native CLI for Sony Alpha cameras (verified on **ILCE-1M2 / A1 II**) using the [Alpha Camera REST API](https://crsdk.app) (`@alpha-sdk/api`).

Controls **in-camera** recording over USB **PC Remote**, shows a live-view window with a red REC tally, sets ISO/shutter/aperture, and pulls clips from CFexpress/SD.

> Live view is a monitoring path. Master quality still comes from the camera’s media — use `sonycam rec` + `sonycam pull --latest`.

## Prerequisites

- macOS Apple Silicon
- Camera USB mode: **PC Remote**
- Node: `npm install -g @alpha-sdk/api` (accept the Sony Camera Remote SDK license on first run)
- Python 3.9+ (3.12 recommended)
- For liveview: `brew install python-tk@3.12` when using Homebrew Python

## Install

```bash
git clone https://github.com/bcharleson/sonycam.git
cd sonycam
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
ln -sf "$(pwd)/.venv/bin/sonycam" ~/.local/bin/sonycam
```

Or: `make install`

## Quick start

```bash
# Camera on + PC Remote + USB connected
sonycam server start
sonycam connect
sonycam status

sonycam set --iso 800 --shutter 1/200
sonycam liveview          # red border while REC
sonycam rec start
sonycam rec stop
sonycam pull --latest --out ~/Movies/sonycam
```

## Commands

| Command | Purpose |
|---------|---------|
| `sonycam server start\|stop\|status` | Local CameraWebApp lifecycle |
| `sonycam connect` | `remote-transfer` + `priority-key=pc-remote` |
| `sonycam status` | Model, ISO, shutter, aperture, REC state |
| `sonycam set --iso/--shutter/--aperture` | Exposure |
| `sonycam rec start\|stop\|toggle\|status` | In-camera movie REC (idempotent start/stop) |
| `sonycam liveview` | JPEG preview + red REC tally |
| `sonycam pull [--latest] [--list]` | List / download card files |
| `sonycam prop <name>` | Raw property dump |

## Agent entry

This repo is meant to be driven by coding agents:

- [`AGENTS.md`](AGENTS.md)
- [`.cursor/skills/sonycam/`](.cursor/skills/sonycam/) — camera ops
- [`.cursor/skills/sonycam-dev/`](.cursor/skills/sonycam-dev/) — develop / extend

## Notes

- `rec` drives the camera’s own recorder (not host MJPEG capture).
- Large CFexpress pulls are async on the Alpha server; destination is the `--out` directory.
- OpenSSL / dylib loading is handled inside `sonycam server start` (`DYLD_LIBRARY_PATH` + Homebrew openssl shim).
- The Sony Camera Remote SDK binary is distributed by `@alpha-sdk/api` under Sony’s license — this repo only ships the Python CLI wrapper (MIT).

## License

MIT — see [`LICENSE`](LICENSE).
