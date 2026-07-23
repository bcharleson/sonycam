---
name: sonycam-dev
description: >-
  Develop and extend the sonycam Sony Alpha CLI: Alpha REST client, CameraWebApp
  server lifecycle, liveview tally UI, CLI flags, and open-source contribution
  workflow. Use when changing sonycam source, fixing USB/API issues, or shipping
  the public repo.
---

# sonycam-dev — build the camera CLI

## Stack (do not replace without strong reason)

- **Python 3.9+** package, CLI via `sonycam.cli:main`
- **stdlib HTTP** (`urllib`) against local Alpha Camera REST API — no required cloud deps
- **Pillow + Tk** only for `liveview`
- Sidecar: `@alpha-sdk/api` → native `CameraWebApp` on `:8080`

## Repo map

| Path | Role |
|------|------|
| `sonycam/api.py` | REST client, property resolve, REC idempotency, pull helpers |
| `sonycam/server.py` | Start/stop CameraWebApp, DYLD + openssl shim |
| `sonycam/cli.py` | argparse commands |
| `sonycam/liveview.py` | Tk preview + red REC tally |
| `.cursor/skills/` | Agent skills |
| `AGENTS.md` | Agent entrypoint |
| `Makefile` | `install` + `smoke` |

## Agent workflow when changing code

```
Dev:
- [ ] 1. Touch only needed modules (keep files ~<300 lines)
- [ ] 2. pip install -e .  (in .venv)
- [ ] 3. sonycam server start && sonycam connect && sonycam status
- [ ] 4. Smoke set / rec status / pull --list (camera on PC Remote)
- [ ] 5. Update CLI help + README + skills if UX changed
- [ ] 6. Sanitize: no camera serials, tokens, or personal absolute paths in docs
```

### Install / smoke

```bash
make install
make smoke          # needs camera connected
```

### Hard rules

1. Master footage path remains **in-camera REC + pull** — don’t ship liveview-as-master.
2. `rec start` / `stop` must stay idempotent via `recording-state`.
3. Never commit camera IDs/serials, local media paths with private names, or `.venv`.
4. Prefer launching `CameraWebApp` **directly** with `DYLD_LIBRARY_PATH` (node `camera-server start` often drops dylibs).
5. Default API base URL is `http://127.0.0.1:8080` (avoid `localhost` IPv6 surprises).
6. If port is open but status hangs, **do not** spawn a second server — tell the user to stop/start.
7. Update both `sonycam` and `sonycam-dev` skills when behavior changes.

## Feature extension guide

| Feature | Where |
|---------|--------|
| New CLI command | `cli.py` + skills/README |
| New property | `api.py` resolve helpers + `set` flags |
| Server reliability | `server.py` |
| Liveview UX | `liveview.py` (lazy-import Tk from CLI) |
| Pull progress / SSE | new small module; keep `api.py` thin |

## Open-source hygiene

- MIT license; Sony CRSDK binary stays a **user-installed** dependency (`@alpha-sdk/api`)
- README uses generic clone paths (`cd sonycam`), not personal home directories
- Example camera IDs in docs must be placeholders (`YOUR_CAMERA_ID`), never a real serial
- `.gitignore` must exclude `.venv/`, `*.egg-info/`, media dumps

## Architecture notes

See [architecture.md](architecture.md).
