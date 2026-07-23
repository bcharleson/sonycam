# AGENTS.md — sonycam

Agent entrypoint for Sony Alpha camera control.

## What this is

`sonycam` drives a Sony Alpha body (verified on ILCE-1M2 / A1 II) over USB **PC Remote** using the local Alpha Camera REST API (`CameraWebApp` on `127.0.0.1:8080`).

It is **not** a screen recorder. Pair with [`screcord`](https://github.com/bcharleson/screcord) for display capture.

## Read these skills

| Skill | When |
|-------|------|
| [`.cursor/skills/sonycam/SKILL.md`](.cursor/skills/sonycam/SKILL.md) | Connect, exposure, REC, liveview, pull |
| [`.cursor/skills/sonycam-dev/SKILL.md`](.cursor/skills/sonycam-dev/SKILL.md) | Change source, build, OSS hygiene |

## Quick commands

```bash
make install
sonycam server start
sonycam connect
sonycam status
sonycam set --iso 800 --shutter 1/200
sonycam liveview
sonycam rec start
sonycam rec stop
sonycam pull --latest --out ~/Movies/sonycam
```

## Non-negotiables

1. Master footage is **in-camera**. Never treat liveview JPEGs as the edit master.
2. Before `rec start`, confirm USB mode is **PC Remote** and `sonycam status` shows connected.
3. `rec start` / `rec stop` must be idempotent via `recording-state` (do not blind-toggle).
4. Keep the Alpha server running for the session; use `sonycam server start` if `:8080` is down.
5. Do not commit secrets, camera serials, or personal absolute home paths into docs.

## Layout

```
sonycam/                 Python package (api, cli, liveview, server)
.cursor/skills/          Agent skills (ops + dev)
.cursor/rules/           Always-on project rule
AGENTS.md                This file
Makefile                 install + smoke
```
