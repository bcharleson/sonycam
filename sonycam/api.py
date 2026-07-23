"""Thin HTTP client for the Alpha Camera REST API (localhost CameraWebApp)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SonyCamError(RuntimeError):
    pass


@dataclass
class Camera:
    id: str
    model: str
    connected: bool
    connection_type: str | None = None


class AlphaAPI:
    def __init__(self, base_url: str = "http://127.0.0.1:8080", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        expect_json: bool = True,
        timeout: float | None = None,
    ) -> Any:
        data = None
        headers: dict[str, str] = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                raw = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                if not expect_json:
                    return raw, content_type, resp.status
                if not raw:
                    return {"success": True}
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise SonyCamError(f"{method} {path} -> HTTP {exc.code}: {detail[:400]}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            reason = getattr(exc, "reason", exc)
            raise SonyCamError(
                f"Cannot reach Alpha API at {self.base_url} ({reason}). "
                "Run: sonycam server start"
            ) from exc

    def server_status(self) -> dict[str, Any]:
        return self._request("GET", "/api/server/status")

    def list_cameras(self) -> list[Camera]:
        payload = self._request("GET", "/api/cameras")
        cameras = []
        for item in payload.get("cameras", []):
            cameras.append(
                Camera(
                    id=item["id"],
                    model=item.get("model", "unknown"),
                    connected=bool(item.get("connected")),
                    connection_type=item.get("connectionType"),
                )
            )
        return cameras

    def connect(
        self,
        camera_id: str,
        mode: str = "remote-transfer",
        reconnecting: str = "on",
        *,
        settle_seconds: float = 1.0,
    ) -> dict[str, Any]:
        result = self._request(
            "POST",
            f"/api/cameras/{camera_id}/connection",
            {"mode": mode, "reconnecting": reconnecting},
        )
        # USB mode transitions can report connected before priority-key is accepted.
        deadline = time.time() + max(settle_seconds, 0.0) + 8.0
        while time.time() < deadline:
            cameras = self.list_cameras()
            cam = next((c for c in cameras if c.id == camera_id), None)
            if cam and cam.connected:
                time.sleep(0.35)
                return result
            time.sleep(0.25)
        return result

    def connect_and_claim(
        self,
        camera_id: str,
        mode: str = "remote-transfer",
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        connect_result: dict[str, Any] = {}
        for attempt in range(3):
            connect_result = self.connect(camera_id, mode=mode)
            for _ in range(6):
                try:
                    priority = self.set_priority_key(camera_id, "pc-remote")
                    return {"connect": connect_result, "priority_key": priority}
                except SonyCamError as exc:
                    last_error = exc
                    time.sleep(0.6)
            # Soft reconnect if the first claim race fails.
            try:
                self.disconnect(camera_id)
            except SonyCamError:
                pass
            time.sleep(0.8 + attempt)
        raise SonyCamError(f"Connected but could not set pc-remote: {last_error}")

    def disconnect(self, camera_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/api/cameras/{camera_id}/connection")

    def set_priority_key(self, camera_id: str, setting: str = "pc-remote") -> dict[str, Any]:
        return self._request(
            "PUT",
            f"/api/cameras/{camera_id}/priority-key",
            {"setting": setting},
        )

    def get_property(self, camera_id: str, name: str) -> dict[str, Any]:
        payload = self._request("GET", f"/api/cameras/{camera_id}/properties/{name}")
        return payload.get("data") or {}

    def set_property(self, camera_id: str, name: str, value: str) -> dict[str, Any]:
        return self._request(
            "PUT",
            f"/api/cameras/{camera_id}/properties/{name}",
            {"value": value},
        )

    def resolve_property_value(self, camera_id: str, name: str, wanted: str) -> str:
        """Map a human value (800, ISO 800, 1/200) to the API value token."""
        prop = self.get_property(camera_id, name)
        available = prop.get("available_values") or []
        wanted_norm = _normalize_label(wanted)
        for entry in available:
            formatted = str(entry.get("formatted", ""))
            value = str(entry.get("value", ""))
            if wanted_norm in {
                _normalize_label(formatted),
                _normalize_label(value),
                _normalize_label(formatted.replace("ISO ", "")),
                _normalize_label(formatted.lstrip("Ff")),
            }:
                return value
            # ISO: accept bare number matching formatted digits
            if name == "iso" and wanted_norm.isdigit():
                digits = "".join(ch for ch in formatted if ch.isdigit())
                if digits == wanted_norm:
                    return value
            # Aperture: accept 2.8 for F2.8
            if name == "aperture":
                fmt_norm = _normalize_label(formatted.lstrip("Ff"))
                if wanted_norm.lstrip("f") == fmt_norm:
                    return value
        current = prop.get("formatted") or prop.get("value")
        choices = ", ".join(str(e.get("formatted")) for e in available[:12])
        raise SonyCamError(
            f"Unknown {name} value {wanted!r} (current={current}). Examples: {choices}"
        )

    def movie_rec_toggle(self, camera_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/cameras/{camera_id}/actions/movie-rec", {})

    def recording_state(self, camera_id: str) -> str:
        prop = self.get_property(camera_id, "recording-state")
        return str(prop.get("formatted") or prop.get("value") or "unknown")

    def ensure_recording(self, camera_id: str, want_recording: bool) -> str:
        state = self.recording_state(camera_id)
        is_recording = state.lower().startswith("recording") and "not" not in state.lower()
        if is_recording == want_recording:
            return state
        self.movie_rec_toggle(camera_id)
        for _ in range(10):
            time.sleep(0.25)
            state = self.recording_state(camera_id)
            is_recording = state.lower().startswith("recording") and "not" not in state.lower()
            if is_recording == want_recording:
                return state
        raise SonyCamError(f"Failed to reach recording={want_recording}; state={state}")

    def live_view_start(self, camera_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/cameras/{camera_id}/live-view/start", {})

    def live_view_stop(self, camera_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/cameras/{camera_id}/live-view/stop", {})

    def live_view_status(self, camera_id: str) -> dict[str, Any]:
        payload = self._request("GET", f"/api/cameras/{camera_id}/live-view/status")
        return payload.get("data") or {}

    def live_view_frame(self, camera_id: str) -> bytes:
        raw, content_type, status = self._request(
            "GET",
            f"/api/cameras/{camera_id}/live-view/frame",
            expect_json=False,
            timeout=5.0,
        )
        if status != 200 or not raw:
            raise SonyCamError("No live-view frame available")
        if not content_type.startswith("image/") and not raw.startswith(b"\xff\xd8"):
            raise SonyCamError(f"Unexpected live-view payload: {content_type}")
        return raw

    def list_files(self, camera_id: str, slot: int = 1) -> list[dict[str, Any]]:
        payload = self._request("GET", f"/api/cameras/{camera_id}/sd-card/slot/{slot}/files")
        return list(payload.get("files") or [])

    def download_file(
        self,
        camera_id: str,
        slot: int,
        content_id: int,
        file_id: int,
        save_path: Path,
    ) -> dict[str, Any]:
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)
        return self._request(
            "POST",
            f"/api/cameras/{camera_id}/sd-card/slot/{slot}/files/{content_id}/{file_id}/download",
            {"save_path": str(save_path)},
            timeout=120.0,
        )


def _normalize_label(value: str) -> str:
    return "".join(value.strip().lower().split())


def file_sort_key(entry: dict[str, Any]) -> tuple:
    return (
        int(entry.get("creation_year") or 0),
        int(entry.get("creation_month") or 0),
        int(entry.get("creation_day") or 0),
        int(entry.get("creation_hour") or 0),
        int(entry.get("creation_minute") or 0),
        int(entry.get("creation_second") or 0),
        int(entry.get("content_id") or 0),
    )


def pick_latest(files: list[dict[str, Any]], *, video_only: bool = True) -> dict[str, Any] | None:
    candidates = files
    if video_only:
        candidates = [
            f
            for f in files
            if str(f.get("file_path", "")).upper().endswith((".MP4", ".MOV", ".MXF"))
        ] or files
    if not candidates:
        return None
    return max(candidates, key=file_sort_key)
