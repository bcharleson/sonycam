"""Start/stop the bundled Alpha CameraWebApp server with correct dylib paths."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from .api import AlphaAPI, SonyCamError

DEFAULT_PORT = 8080
DEFAULT_BASE_URL = f"http://127.0.0.1:{DEFAULT_PORT}"


def ensure_openssl_shim() -> None:
    """Bundled libssl may hardcode Homebrew Cellar openssl@3/3.6.1."""
    cellar = Path("/opt/homebrew/Cellar/openssl@3")
    missing = cellar / "3.6.1"
    opt = Path("/opt/homebrew/opt/openssl@3")
    if not cellar.exists() or not opt.exists():
        return
    target_name = opt.resolve().name
    if not (cellar / target_name).exists():
        return
    # Refresh stale shim after `brew upgrade openssl@3`.
    if missing.is_symlink() or missing.exists():
        try:
            if missing.resolve() == (cellar / target_name).resolve():
                return
            if missing.is_symlink() or missing.is_dir():
                if missing.is_symlink():
                    missing.unlink()
        except OSError:
            return
    try:
        missing.symlink_to(target_name)
    except OSError:
        pass

def _sdk_darwin_dir() -> Path | None:
    candidates = [
        Path.home()
        / ".npm-global/lib/node_modules/@alpha-sdk/api/node_modules/@alpha-sdk/darwin-arm64",
        Path("/opt/homebrew/lib/node_modules/@alpha-sdk/api/node_modules/@alpha-sdk/darwin-arm64"),
        Path.home()
        / ".npm-global/lib/node_modules/@alpha-sdk/darwin-arm64",
    ]
    for path in candidates:
        if (path / "CameraWebApp").exists():
            return path
    return None


def camera_webapp_env() -> dict[str, str]:
    env = os.environ.copy()
    sdk = _sdk_darwin_dir()
    openssl = Path("/opt/homebrew/opt/openssl@3/lib")
    lib_paths: list[str] = []
    if sdk is not None:
        lib_paths.append(str(sdk / "lib"))
    if openssl.exists():
        lib_paths.append(str(openssl))
    existing = env.get("DYLD_LIBRARY_PATH", "")
    if existing:
        lib_paths.append(existing)
    if lib_paths:
        env["DYLD_LIBRARY_PATH"] = ":".join(lib_paths)
    return env


def _port_open(port: int = DEFAULT_PORT) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        try:
            return sock.connect_ex(("127.0.0.1", port)) == 0
        except OSError:
            return False


def is_server_up(base_url: str = DEFAULT_BASE_URL) -> bool:
    try:
        AlphaAPI(base_url, timeout=8.0).server_status()
        return True
    except SonyCamError:
        return False


def start_server(port: int = DEFAULT_PORT, *, wait_seconds: float = 25.0) -> None:
    ensure_openssl_shim()
    base = f"http://127.0.0.1:{port}"
    if is_server_up(base):
        return
    if _port_open(port):
        # Avoid stacking CameraWebApp instances when status is slow/busy.
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            if is_server_up(base):
                return
            time.sleep(0.5)
        raise SonyCamError(
            f"Port {port} is open but Alpha API is not responding. "
            "Run: sonycam server stop && sonycam server start"
        )

    env = camera_webapp_env()
    sdk = _sdk_darwin_dir()
    if sdk is None:
        raise SonyCamError(
            "Alpha SDK not found. Install with: npm install -g @alpha-sdk/api"
        )
    binary = sdk / "CameraWebApp"
    # Prefer launching the binary directly so DYLD_LIBRARY_PATH applies.
    # `camera-server start` spawns via node and often drops the dylib path.
    log_path = Path("/tmp/sonycam-camerawebapp.log")
    with log_path.open("ab") as log:
        subprocess.Popen(
            [str(binary)],
            env=env,
            cwd=str(sdk),
            stdout=log,
            stderr=log,
            start_new_session=True,
        )

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if is_server_up(base):
            return
        time.sleep(0.25)
    raise SonyCamError(
        f"camera-server did not become ready on :{port}. See {log_path}"
    )


def stop_server(port: int = DEFAULT_PORT) -> None:
    base = f"http://127.0.0.1:{port}"
    try:
        AlphaAPI(base, timeout=2.0)._request("POST", "/api/server/shutdown", {})
    except Exception:
        pass
    subprocess.run(["pkill", "-f", "CameraWebApp"], check=False, capture_output=True)


def ensure_server(port: int = DEFAULT_PORT) -> None:
    ensure_openssl_shim()
    if not is_server_up(f"http://127.0.0.1:{port}"):
        start_server(port)
