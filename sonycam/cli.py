"""sonycam CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import __version__
from .api import AlphaAPI, SonyCamError, pick_latest
from .server import ensure_server, is_server_up, start_server, stop_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sonycam",
        description="Control a Sony Alpha camera (A1 II / etc.) via Alpha Camera REST API",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument("--version", action="version", version=f"sonycam {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_server = sub.add_parser("server", help="Manage the local Alpha CameraWebApp server")
    p_server_sub = p_server.add_subparsers(dest="server_cmd", required=True)
    p_server_sub.add_parser("start")
    p_server_sub.add_parser("stop")
    p_server_sub.add_parser("status")

    sub.add_parser("status", help="Server + camera connection / exposure / REC state")
    p_connect = sub.add_parser("connect", help="Connect camera in remote-transfer + pc-remote")
    p_connect.add_argument("--mode", default="remote-transfer", choices=["remote", "remote-transfer", "contents"])

    p_set = sub.add_parser("set", help="Set exposure properties")
    p_set.add_argument("--iso", help="ISO value, e.g. 800 or ISO 800")
    p_set.add_argument("--shutter", help="Shutter, e.g. 1/200")
    p_set.add_argument("--aperture", "--fnumber", dest="aperture", help="Aperture, e.g. 2.8")

    p_rec = sub.add_parser("rec", help="Start/stop in-camera movie recording")
    p_rec.add_argument("action", choices=["start", "stop", "toggle", "status"])

    p_lv = sub.add_parser("liveview", help="Open live-view window with red REC tally")
    p_lv.add_argument("--fps", type=float, default=12.0)
    p_lv.add_argument("--display", type=int, default=1, help="Preferred display index (1=second)")

    p_pull = sub.add_parser("pull", help="Download files from camera SD/CFexpress")
    p_pull.add_argument("--latest", action="store_true", help="Download newest video clip")
    p_pull.add_argument("--slot", type=int, default=1)
    p_pull.add_argument(
        "--out",
        default=str(Path.home() / "Movies" / "sonycam"),
        help="Destination directory",
    )
    p_pull.add_argument("--list", action="store_true", help="List files only")

    p_prop = sub.add_parser("prop", help="Get a raw property")
    p_prop.add_argument("name")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "server":
            return _cmd_server(args)
        api = AlphaAPI(args.base_url)
        ensure_server()
        camera_id = _require_camera(api)
        if args.cmd == "status":
            return _cmd_status(api, camera_id, as_json=args.json)
        if args.cmd == "connect":
            return _cmd_connect(api, camera_id, mode=args.mode, as_json=args.json)
        if args.cmd == "set":
            return _cmd_set(api, camera_id, args, as_json=args.json)
        if args.cmd == "rec":
            return _cmd_rec(api, camera_id, args.action, as_json=args.json)
        if args.cmd == "liveview":
            from .liveview import run_liveview

            _ensure_connected(api, camera_id)
            run_liveview(
                api,
                camera_id,
                fps=args.fps,
                display_index=args.display,
                title=f"sonycam — {camera_id}",
            )
            return 0
        if args.cmd == "pull":
            return _cmd_pull(api, camera_id, args, as_json=args.json)
        if args.cmd == "prop":
            data = api.get_property(camera_id, args.name)
            _emit(data, as_json=True)
            return 0
        parser.error(f"unknown command {args.cmd}")
        return 2
    except SonyCamError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _cmd_server(args: argparse.Namespace) -> int:
    if args.server_cmd == "start":
        start_server()
        print("server ready on http://localhost:8080")
        return 0
    if args.server_cmd == "stop":
        stop_server()
        print("server stop requested")
        return 0
    up = is_server_up()
    print("up" if up else "down")
    if up:
        api = AlphaAPI(args.base_url)
        _emit(api.server_status(), as_json=args.json)
    return 0 if up else 1


def _cmd_status(api: AlphaAPI, camera_id: str, *, as_json: bool) -> int:
    cameras = api.list_cameras()
    cam = next(c for c in cameras if c.id == camera_id)
    payload = {
        "server": api.server_status().get("server"),
        "camera": {
            "id": cam.id,
            "model": cam.model,
            "connected": cam.connected,
            "connection_type": cam.connection_type,
        },
    }
    if cam.connected:
        for name in ("iso", "shutter-speed", "aperture", "recording-state"):
            try:
                prop = api.get_property(camera_id, name)
                payload[name] = {
                    "formatted": prop.get("formatted"),
                    "value": prop.get("value"),
                }
            except SonyCamError as exc:
                payload[name] = {"error": str(exc)}
        try:
            payload["live_view"] = api.live_view_status(camera_id)
        except SonyCamError as exc:
            payload["live_view"] = {"error": str(exc)}
    if as_json:
        _emit(payload, as_json=True)
    else:
        c = payload["camera"]
        print(f"{c['model']}  id={c['id']}  connected={c['connected']}  via={c.get('connection_type')}")
        if cam.connected:
            print(
                f"ISO {payload['iso'].get('formatted')}  "
                f"shutter {payload['shutter-speed'].get('formatted')}  "
                f"{payload['aperture'].get('formatted')}  "
                f"REC {payload['recording-state'].get('formatted')}"
            )
    return 0


def _cmd_connect(api: AlphaAPI, camera_id: str, *, mode: str, as_json: bool) -> int:
    result = api.connect_and_claim(camera_id, mode=mode)
    payload = {**result, "camera_id": camera_id, "mode": mode}
    _emit(payload, as_json=as_json)
    if not as_json:
        print(f"connected {camera_id} mode={mode} priority=pc-remote")
    return 0


def _cmd_set(api: AlphaAPI, camera_id: str, args: argparse.Namespace, *, as_json: bool) -> int:
    _ensure_connected(api, camera_id)
    changed: dict[str, str] = {}
    if args.iso:
        value = api.resolve_property_value(camera_id, "iso", args.iso)
        api.set_property(camera_id, "iso", value)
        time.sleep(0.35)
        changed["iso"] = api.get_property(camera_id, "iso").get("formatted", value)
    if args.shutter:
        value = api.resolve_property_value(camera_id, "shutter-speed", args.shutter)
        api.set_property(camera_id, "shutter-speed", value)
        time.sleep(0.35)
        changed["shutter-speed"] = api.get_property(camera_id, "shutter-speed").get(
            "formatted", value
        )
    if args.aperture:
        value = api.resolve_property_value(camera_id, "aperture", args.aperture)
        api.set_property(camera_id, "aperture", value)
        time.sleep(0.35)
        changed["aperture"] = api.get_property(camera_id, "aperture").get("formatted", value)
    if not changed:
        raise SonyCamError("Nothing to set. Pass --iso and/or --shutter and/or --aperture")
    _emit(changed, as_json=as_json)
    if not as_json:
        for key, val in changed.items():
            print(f"{key} = {val}")
    return 0


def _cmd_rec(api: AlphaAPI, camera_id: str, action: str, *, as_json: bool) -> int:
    _ensure_connected(api, camera_id)
    if action == "status":
        state = api.recording_state(camera_id)
    elif action == "toggle":
        api.movie_rec_toggle(camera_id)
        state = api.recording_state(camera_id)
    elif action == "start":
        state = api.ensure_recording(camera_id, True)
    else:
        state = api.ensure_recording(camera_id, False)
    payload = {"recording_state": state}
    _emit(payload, as_json=as_json)
    if not as_json:
        print(state)
    return 0


def _cmd_pull(api: AlphaAPI, camera_id: str, args: argparse.Namespace, *, as_json: bool) -> int:
    _ensure_connected(api, camera_id)
    files = api.list_files(camera_id, slot=args.slot)
    if args.list or not args.latest:
        rows = []
        for entry in sorted(files, key=lambda f: (
            int(f.get("creation_year") or 0),
            int(f.get("creation_month") or 0),
            int(f.get("creation_day") or 0),
            int(f.get("creation_hour") or 0),
            int(f.get("creation_minute") or 0),
            int(f.get("creation_second") or 0),
        )):
            rows.append(
                {
                    "path": entry.get("file_path"),
                    "size": entry.get("file_size"),
                    "content_id": entry.get("content_id"),
                    "file_id": entry.get("file_id"),
                    "created": (
                        f"{entry.get('creation_year')}-"
                        f"{int(entry.get('creation_month') or 0):02d}-"
                        f"{int(entry.get('creation_day') or 0):02d} "
                        f"{int(entry.get('creation_hour') or 0):02d}:"
                        f"{int(entry.get('creation_minute') or 0):02d}:"
                        f"{int(entry.get('creation_second') or 0):02d}"
                    ),
                }
            )
        if as_json:
            _emit({"files": rows}, as_json=True)
        else:
            for row in rows:
                print(f"{row['created']}  {row['size']:>12}  {row['path']}")
        if not args.latest:
            return 0

    latest = pick_latest(files, video_only=True)
    if latest is None:
        raise SonyCamError("No files found on slot")
    out = Path(args.out).expanduser()
    result = api.download_file(
        camera_id,
        args.slot,
        int(latest["content_id"]),
        int(latest["file_id"]),
        out,
    )
    payload = {"file": latest, "download": result, "out": str(out)}
    _emit(payload, as_json=as_json)
    if not as_json:
        print(f"downloading {latest.get('file_path')} -> {out}")
        print("(transfer runs on the Alpha server; watch CameraWebApp / SSE for progress)")
    return 0


def _require_camera(api: AlphaAPI) -> str:
    cameras = api.list_cameras()
    if not cameras:
        raise SonyCamError(
            "No cameras discovered. Power on, set USB to PC Remote, and reconnect the cable."
        )
    # Prefer already-connected, else first discovered.
    connected = [c for c in cameras if c.connected]
    chosen = connected[0] if connected else cameras[0]
    return chosen.id


def _ensure_connected(api: AlphaAPI, camera_id: str) -> None:
    cameras = api.list_cameras()
    cam = next((c for c in cameras if c.id == camera_id), None)
    if cam is None:
        raise SonyCamError(f"Camera {camera_id} not found")
    if not cam.connected:
        api.connect_and_claim(camera_id, mode="remote-transfer")


def _emit(payload: object, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
