from __future__ import annotations

import threading
import json
import time
from typing import Any, Callable, Dict, Optional, Mapping
from dataclasses import dataclass
import websocket

# MoonrakerWSClient: the only public class.
class MoonrakerWSClient:
    """Pure Moonraker WebSocket client: safe, boring, thread-safe, and responsibility-limited."""

    # -- Construction and state
    def __init__(self, ws_url: str, recv_timeout_s: float = 0.25):
        self._ws_url = ws_url
        self._recv_timeout_s = recv_timeout_s

        self._ws: Optional[websocket.WebSocket] = None
        self._rx_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._send_lock = threading.Lock()
        self._pending_lock = threading.Lock()
        self._pending: Dict[int, _PendingRequest] = {}
        self._next_id = 1
        self._notifier_lock = threading.Lock()
        self._notif_handlers: Dict[str, Callable[[dict], None]] = {} 
        self._cache_lock = threading.Lock()
        self._printer_state: Dict[str, Any] = {}
        self._printer_status_time: Optional[float] = None

    # -- Connection lifecycle

    def connect(self) -> None:
        """Establish WebSocket and start receiver thread. Only invoked by caller."""
        if self.is_connected():
            return

        try:
            ws = websocket.create_connection(self._ws_url, timeout=5)
            ws.settimeout(self._recv_timeout_s)
        except Exception as e:
            self._ws = None
            raise RuntimeError(f"Failed to connect to Moonraker: {e}") from e
        self._ws = ws
        self._stop.clear()
        rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread = rx_thread
        rx_thread.start()

        # Subscribe to printer status objects -- allowed to stub
        try:
            self.call("printer.objects.subscribe", {"objects": ["print_stats", "toolhead", "virtual_sdcard", "idle_timeout", "display_status"]})
        except Exception:
            # Subscriptions are best-effort and stubbed (do not block connect)
            pass

    def close(self) -> None:
        """Clean shutdown. Safe to call multiple times."""
        self._stop.set()
        ws, rx = self._ws, self._rx_thread
        self._ws = None
        self._rx_thread = None

        if ws:
            try:
                ws.close()
            except Exception:
                pass

        if rx and rx.is_alive() and threading.current_thread() != rx:
            rx.join(timeout=2)

        with self._pending_lock:
            for p in self._pending.values():
                p.finish(error=RuntimeError("WebSocket closed"))
            self._pending.clear()

    def is_connected(self) -> bool:
        """True if a WebSocket exists, the receive thread is alive, and not shutting down."""
        return (
            self._ws is not None and
            self._rx_thread is not None and
            self._rx_thread.is_alive() and
            not self._stop.is_set()
        )

    # -- JSON-RPC

    def call(self, method: str, params: Optional[dict] = None, timeout_s: float = 2.0) -> dict:
        """Send a JSON-RPC request and await response, matched by id."""
        if not self.is_connected():
            raise RuntimeError("WebSocket not connected")
        with self._pending_lock:
            req_id = self._next_id
            self._next_id += 1
        msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            msg["params"] = params
        pending = _PendingRequest()
        with self._pending_lock:
            self._pending[req_id] = pending

        txt = json.dumps(msg)
        try:
            with self._send_lock:
                ws = self._ws
                if not ws:
                    raise websocket.WebSocketConnectionClosedException("WebSocket is None")
                ws.send(txt)
        except Exception as e:
            with self._pending_lock:
                self._pending.pop(req_id, None)
            pending.finish(error=e)
            raise RuntimeError("Send failed") from e

        if not pending.event.wait(timeout_s):
            with self._pending_lock:
                self._pending.pop(req_id, None)
            pending.finish(error=TimeoutError(f"Timeout waiting for {method}"))
            raise TimeoutError(f"Moonraker WS call timeout: {method}")

        if pending.error:
            raise pending.error
        if pending.response is None:
            raise RuntimeError("No response received")
        return pending.response

    def send_gcode(self, gcode: str) -> None:
        """Send G-code via Moonraker (non-blocking fire-and-forget)."""
        if not self.is_connected():
            raise RuntimeError("WebSocket not connected")
        
        msg = {
            "jsonrpc": "2.0",
            "method": "server.gcode_script",
            "params": {"script": gcode}
        }
        
        txt = json.dumps(msg)
        try:
            with self._send_lock:
                ws = self._ws
                if not ws:
                    raise websocket.WebSocketConnectionClosedException("WebSocket is None")
                ws.send(txt)
        except Exception as e:
            # Explicitly do not register a pending for response
            raise RuntimeError("Failed to send gcode") from e

    # -- Printer state mirroring

    def _update_printer_state(self, notification: dict) -> None:
        """
        Mirror Moonraker printer state exactly as received.
        No interpretation, no inference, no control logic.
        """
        params = notification.get("params") or []
        if not params or not isinstance(params[0], dict):
            return

        with self._cache_lock:
            self._printer_state.update(params[0])
            self._printer_status_time = time.time()

    @property
    def printer_status_time(self) -> Optional[float]:
        """Timestamp of last printer status update (epoch seconds)."""
        with self._cache_lock:
            return self._printer_status_time

    @property
    def cached_printer_state(self) -> Mapping[str, Any]:
        """Debug snapshot of mirrored printer state (deepcopy not warranted; output is read-only for inspection)."""
        with self._cache_lock:
            return dict(self._printer_state)

    # -- Notification handlers

    def on_notify(self, method: str, handler: Callable[[dict], None]) -> None:
        """Register a Moonraker notification handler."""
        with self._notifier_lock:
            self._notif_handlers[method] = handler

    # -- Internal receive thread

    def _rx_loop(self) -> None:
        ws = self._ws
        while ws and not self._stop.is_set():
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except websocket.WebSocketConnectionClosedException:
                break
            except Exception:
                break

            if raw is None:
                continue
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            # Response to a request
            if isinstance(msg, dict) and "id" in msg:
                req_id = msg["id"]
                with self._pending_lock:
                    pending = self._pending.pop(req_id, None)
                if pending:
                    pending.finish(response=msg)
                continue

            # Notifications
            if isinstance(msg, dict) and "method" in msg:
                method = msg.get("method", "")
                if method == "notify_status_update":
                    self._update_printer_state(msg)
                with self._notifier_lock:
                    cb = self._notif_handlers.get(method)
                if cb:
                    try:
                        cb(msg)
                    except Exception:
                        pass  # Handler must never raise
        # On exit: fail any outstanding requests.
        with self._pending_lock:
            for p in self._pending.values():
                p.finish(error=RuntimeError("WebSocket receive loop terminated"))
            self._pending.clear()
        self._ws = None

# -- Internal support dataclasses --

@dataclass
class _PendingRequest:
    response: Optional[dict] = None
    error: Optional[Exception] = None

    def __post_init__(self):
        self.event = threading.Event()

    def finish(self, response: Optional[dict] = None, error: Optional[Exception] = None):
        self.response = response
        self.error = error
        self.event.set()
