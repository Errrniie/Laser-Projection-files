import websocket, json
import threading
from __future__ import annotations

from Motion.Moonraker_ws import MoonrakerWSClient

MOONRAKER_WS = "ws://192.168.8.127:7125/websocket"

_ws = None
_ws_lock = threading.Lock()

def init_ws():
    global _ws
    _ws = websocket.create_connection(MOONRAKER_WS)
    _ws.send(json.dumps({
        "jsonrpc": "2.0",
        "method": "printer.objects.subscribe",
        "params": {"objects": {"gcode": ["responses"]}},
        "id": 1
    }))

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
    # Moonraker responses are JSON-RPC: {"result": ...} or {"error": ...}
    if "error" in resp:
        raise RuntimeError(resp["error"])

