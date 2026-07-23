# sonycam CLI reference

## Global flags

| Flag | Default | Notes |
|------|---------|-------|
| `--base-url` | `http://127.0.0.1:8080` | Alpha CameraWebApp |
| `--json` | off | Machine-readable where supported |
| `--version` | | Package version |

## Commands

### `server start|stop|status`

Manages the local `CameraWebApp` binary from `@alpha-sdk/darwin-arm64`.

- Sets `DYLD_LIBRARY_PATH` to SDK `lib` + Homebrew `openssl@3`
- Ensures Cellar shim if bundled `libssl` pins an older openssl path
- Binds `127.0.0.1:8080`

### `connect [--mode remote-transfer|remote|contents]`

Default `remote-transfer` (control + explicit SD/CFexpress access), then `priority-key=pc-remote`.

### `status`

Prints model, connection, ISO, shutter, aperture, REC state. `--json` for agents.

### `set`

| Flag | Property | Examples |
|------|----------|----------|
| `--iso` | `iso` | `800`, `ISO 800` |
| `--shutter` | `shutter-speed` | `1/200` |
| `--aperture` / `--fnumber` | `aperture` | `2.8`, `F2.8` |

Values are resolved against the camera’s `available_values`.

### `rec start|stop|toggle|status`

Maps to `POST .../actions/movie-rec` (toggle) with `recording-state` for idempotent start/stop.

### `liveview [--fps 12] [--display 1]`

Starts live-view worker, polls JPEG frames, Tk window with red REC tally.
Requires Tk (`brew install python-tk@3.12` for Homebrew Python).

### `pull`

| Flag | Notes |
|------|-------|
| `--list` | List slot files (default if not `--latest`) |
| `--latest` | Download newest video clip |
| `--slot N` | Default `1` |
| `--out DIR` | Default `~/Movies/sonycam` |

Download is async on the Alpha server; watch server logs / SSE for large files.

### `prop <name>`

Raw property dump (`iso`, `shutter-speed`, `aperture`, `recording-state`, …).

## Alpha REST map (v3)

| Action | HTTP |
|--------|------|
| List cameras | `GET /api/cameras` |
| Connect | `POST /api/cameras/{id}/connection` |
| Priority | `PUT /api/cameras/{id}/priority-key` |
| Property get/set | `GET|PUT /api/cameras/{id}/properties/{name}` |
| Movie REC | `POST /api/cameras/{id}/actions/movie-rec` |
| Live view start/stop | `POST .../live-view/start\|stop` |
| Live view frame | `GET .../live-view/frame` |
| List files | `GET .../sd-card/slot/{n}/files` |
| Download | `POST .../sd-card/slot/{n}/files/{contentId}/{fileId}/download` |

Docs: https://crsdk.app
