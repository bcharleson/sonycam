"""Tk live-view window with a red REC tally border."""

from __future__ import annotations

import io
import threading
import time
import tkinter as tk
from PIL import Image, ImageTk

from .api import AlphaAPI, SonyCamError


def run_liveview(
    api: AlphaAPI,
    camera_id: str,
    *,
    title: str = "sonycam liveview",
    fps: float = 12.0,
    display_index: int | None = None,
) -> None:
    """Block until the window is closed. Polls JPEG frames + recording-state."""
    api.live_view_start(camera_id)

    root = tk.Tk()
    root.title(title)
    root.configure(bg="#111111")

    border = tk.Frame(root, bg="#222222", padx=10, pady=10)
    border.pack(fill=tk.BOTH, expand=True)

    label = tk.Label(border, bg="#111111")
    label.pack(fill=tk.BOTH, expand=True)

    tally = tk.Label(
        root,
        text="STANDBY",
        fg="#f2f2f2",
        bg="#222222",
        font=("Menlo", 16, "bold"),
        pady=8,
    )
    tally.pack(fill=tk.X)

    state = {
        "photo": None,
        "recording": False,
        "stop": False,
        "error": None,
        "last_frame": None,
    }
    lock = threading.Lock()
    interval = 1.0 / max(fps, 1.0)

    def poller() -> None:
        while not state["stop"]:
            started = time.time()
            try:
                frame = api.live_view_frame(camera_id)
                rec = api.recording_state(camera_id)
                recording = rec.lower().startswith("recording") and "not" not in rec.lower()
                with lock:
                    state["last_frame"] = frame
                    state["recording"] = recording
                    state["error"] = None
            except SonyCamError as exc:
                with lock:
                    state["error"] = str(exc)
            elapsed = time.time() - started
            time.sleep(max(0.0, interval - elapsed))

    thread = threading.Thread(target=poller, name="sonycam-liveview", daemon=True)
    thread.start()

    def tick() -> None:
        with lock:
            frame = state["last_frame"]
            recording = state["recording"]
            error = state["error"]
        if frame:
            image = Image.open(io.BytesIO(frame))
            # Fit to a reasonable monitor preview size while keeping aspect.
            image.thumbnail((1600, 900), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            label.configure(image=photo)
            state["photo"] = photo  # keep reference
        if recording:
            border.configure(bg="#e10600", padx=14, pady=14)
            tally.configure(text="● REC", bg="#e10600", fg="#ffffff")
            root.configure(bg="#e10600")
        else:
            border.configure(bg="#222222", padx=10, pady=10)
            msg = "STANDBY" if not error else f"STANDBY ({error[:48]})"
            tally.configure(text=msg, bg="#222222", fg="#f2f2f2")
            root.configure(bg="#111111")
        root.after(33, tick)

    def on_close() -> None:
        state["stop"] = True
        try:
            api.live_view_stop(camera_id)
        except SonyCamError:
            pass
        root.destroy()

    if display_index is not None:
        # Best-effort placement: Tk can't query NSScreen cleanly without PyObjC.
        # Offset far right for a second monitor when requested.
        if display_index > 0:
            root.geometry("+1920+80")

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(50, tick)
    root.mainloop()
