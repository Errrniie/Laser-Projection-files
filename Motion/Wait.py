from __future__ import annotations

from Motion.Moonraker_ws import MoonrakerWSClient

def wait_for_complete(ws_client: MoonrakerWSClient, timeout_s: float = 10.0) -> None:
    """
    Blocks until all queued moves complete.
    Uses M400 (wait for moves to finish).
    """
    resp = ws_client.call(
        "printer.gcode.script",
        {"script": "M400"},
        timeout_s=timeout_s
    )
    if "error" in resp:
        raise RuntimeError(resp["error"])
