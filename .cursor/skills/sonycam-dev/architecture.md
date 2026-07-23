# sonycam architecture

```
┌─────────────┐     HTTP/SSE      ┌──────────────────┐     USB PC Remote
│  sonycam    │ ───────────────► │  CameraWebApp    │ ──────────────────► Alpha body
│  CLI/Python │   :8080          │  (@alpha-sdk)    │
└─────────────┘                  └──────────────────┘
       │
       │ JPEG poll
       ▼
┌─────────────┐
│ liveview Tk │  red tally from recording-state
└─────────────┘
```

## Connection modes

| Mode | Control | Card access |
|------|---------|-------------|
| `remote` | Yes | Auto-transfer stills (less useful for movie pull) |
| `remote-transfer` | Yes | Explicit list/download (**default**) |
| `contents` | No | Card only |

After connect, `priority-key=pc-remote` is required before most sets/actions.

## Quality path

1. Operator/agent sets exposure
2. Optional liveview for framing / REC tally
3. `movie-rec` toggles **in-camera** recorder (XAVC etc. on CFexpress)
4. `pull --latest` copies the master file to the host

Liveview frames are low-res JPEG monitoring — not substitutes for card media.

## Failure modes worth knowing

- **Bundled libssl → missing Cellar openssl path** after `brew upgrade openssl@3` → shim in `server.ensure_openssl_shim`
- **Second CameraWebApp on :8080** wedges status (accepts TCP, no response) → stop before start
- **Creators’ App / other PTP clients** can steal USB exclusive access
- **Property set race** right after connect → `connect_and_claim` retries
