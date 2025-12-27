from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional

import websocket


# ============================================================
# Moonraker WebSocket Client
# ============================================================

class MoonrakerWSClient:
    """
    Thin, thread-safe Moonraker WebSocket client.

    Responsibilities:
    - Maintain a WebSocket connection
    - Send JSON-RPC requests
    - Match responses by request ID
    - Mirror printer state from notifications
    - Dispatch notifications to registered handlers

    Non-responsibilities:
    - Motion control logic
    - State machines
    - Timing / coordination logic
    """

    # --------------------------------------------------------
    # Construction & Internal State
    # --------------------------------------------------------

    def __init__(self, ws_url: str, recv_timeout_s: float = 0.25):
        # Connection config
        self._ws_url = ws_url
        self._recv_timeout_s = recv_timeout_s

        # WebSocket + RX thread
        self._ws: Optional[websocket.WebSocket] = None
        self._rx_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Locks
        self._send_lock = threading.Lock()
        self._pending_lock = threading.Lock()
        self._notifier_lock = threading.Lock()
        self._cache_lock = threading.Lock()

        # JSON-RPC request tracking
        self._next_id: int = 1
        self._pending: Dict[int, _PendingRequest] = {}

        # Notification handlers
        self._notif_handlers: Dict[str, Callable[[dict], None]] = {}

        # Cached printer state
        self._printer_state: Dict[str, Any] = {}
        self._printer_status_time: Optional[float] = None

    # --------------------------------------------------------
    # Connection Lifecycle
    # --------------------------------------------------------

    def connect(self) -> None:
        """Open WebSocket connection and start receive thread."""
        if self.is_connected():
            return

        try:
            ws = websocket.create_connection(self._ws_url, timeout=5)
            ws.settimeout(self._recv_timeout_s)
        except Exception as exc:
            raise RuntimeError(f"Failed to connect to Moonraker: {exc}") from exc

        self._ws = ws
        self._stop_event.clear()

        self._rx_thread = threading.Thread(
            target=self._rx_loop,
            name="MoonrakerWS-RX",
            daemon=True,
        )
        self._rx_thread.start()

        # Best-effort subscription to printer state
        try:
            self.call(
                "printer.objects.subscribe",
                {
                    "objects": {
                        "print_stats": None,
                        "toolhead": None,
                        "virtual_sdcard": None,
                        "idle_timeout": None,
                        "display_status": None,
                    }
                },
            )
        # After subscription, fetch initial printer state to seed _printer_state
        # --- ADD THIS BLOCK ---
            # Fetch initial printer state to seed print_stats
            resp = self.call(
                "printer.objects.query",
                {"objects": {"print_stats": None}},
                timeout_s=2.0,
            )
            status = resp.get("result", {}).get("status", {})
            if status:
                with self._cache_lock:
                    self._printer_state.update(status)
                    self._printer_status_time = time.time()
        except Exception:
            pass  # Do not block connection on subscription failure
            
    def close(self) -> None:
        """Shut down RX thread, close socket, fail pending requests."""
        self._stop_event.set()

        ws = self._ws
        rx = self._rx_thread

        self._ws = None
        self._rx_thread = None

        if ws:
            try:
                ws.close()
            except Exception:
                pass

        if rx and rx.is_alive() and threading.current_thread() is not rx:
            rx.join(timeout=2)

        # Fail any pending RPC calls
        with self._pending_lock:
            for pending in self._pending.values():
                pending.finish(error=RuntimeError("WebSocket closed"))
            self._pending.clear()

    def is_connected(self) -> bool:
        """Return True if socket and RX thread are alive."""
        return (
            self._ws is not None
            and self._rx_thread is not None
            and self._rx_thread.is_alive()
            and not self._stop_event.is_set()
        )

    # --------------------------------------------------------
    # JSON-RPC API
    # --------------------------------------------------------

    def call(
        self,
        method: str,
        params: Optional[dict] = None,
        timeout_s: float = 2.0,
    ) -> dict:
        """Send a JSON-RPC request and block until response."""
        if not self.is_connected():
            raise RuntimeError("WebSocket not connected")

        # Allocate request ID
        with self._pending_lock:
            req_id = self._next_id
            self._next_id += 1

        message = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            message["params"] = params

        pending = _PendingRequest()
        with self._pending_lock:
            self._pending[req_id] = pending

        # Send request
        try:
            with self._send_lock:
                if not self._ws:
                    raise websocket.WebSocketConnectionClosedException()
                self._ws.send(json.dumps(message))
        except Exception as exc:
            with self._pending_lock:
                self._pending.pop(req_id, None)
            pending.finish(error=exc)
            raise RuntimeError("Send failed") from exc

        # Wait for response
        if not pending.event.wait(timeout_s):
            with self._pending_lock:
                self._pending.pop(req_id, None)
            pending.finish(error=TimeoutError(method))
            raise TimeoutError(f"Moonraker WS timeout: {method}")

        if pending.error:
            raise pending.error

        if pending.response is None:
            raise RuntimeError("No response received")

        return pending.response

    def send_gcode(self, gcode: str) -> None:
        print("Moonraker send_gcode called")
        print(gcode)

        msg = {
            "jsonrpc": "2.0",
            "method": "printer.gcode.script",
            "params": {"script": gcode}
        }

        txt = json.dumps(msg)

        with self._send_lock:
            ws = self._ws
            if not ws:
                raise RuntimeError("WebSocket is None")
            ws.send(txt)

        print("Moonraker WS SEND OK")


    # --------------------------------------------------------
    # Printer State Helpers
    # --------------------------------------------------------

    @property
    def is_idle(self) -> Optional[bool]:
        state = self._printer_state.get("print_stats")
        if not isinstance(state, dict):
            return None

        status = state.get("state")
        if not status:
            return None

        status = status.lower()
        if status in ("standby", "ready", "complete"):
            return True
        if status in ("printing", "paused"):
            return False

        return None


    def _update_printer_state(self, notification: dict) -> None:
        params = notification.get("params")
        if not isinstance(params, list) or not params:
            return
        if not isinstance(params[0], dict):
            return

        with self._cache_lock:
            self._printer_state.update(params[0])
            self._printer_status_time = time.time()

    @property
    def cached_printer_state(self) -> Mapping[str, Any]:
        with self._cache_lock:
            return dict(self._printer_state)

    @property
    def printer_status_time(self) -> Optional[float]:
        with self._cache_lock:
            return self._printer_status_time

    # --------------------------------------------------------
    # Notification Registration
    # --------------------------------------------------------

    def on_notify(self, method: str, handler: Callable[[dict], None]) -> None:
        """Register a callback for Moonraker notifications."""
        with self._notifier_lock:
            self._notif_handlers[method] = handler

    # --------------------------------------------------------
    # RX Thread
    # --------------------------------------------------------

    def _rx_loop(self) -> None:
        ws = self._ws

        while ws and not self._stop_event.is_set():
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except websocket.WebSocketConnectionClosedException:
                break
            except Exception:
                break

            if not raw:
                continue

            try:
                msg = json.loads(raw)
            except Exception:
                continue

            # JSON-RPC response
            if isinstance(msg, dict) and "id" in msg:
                with self._pending_lock:
                    pending = self._pending.pop(msg["id"], None)
                if pending:
                    pending.finish(response=msg)
                continue

            # Notification
            if isinstance(msg, dict) and "method" in msg:
                if isinstance(msg.get("params"), list):
                    self._update_printer_state(msg)

                with self._notifier_lock:
                    handler = self._notif_handlers.get(msg["method"])

                if handler:
                    try:
                        handler(msg)
                    except Exception:
                        pass  # Notification handlers must not raise

        # Fail outstanding requests on exit
        with self._pending_lock:
            for pending in self._pending.values():
                pending.finish(
                    error=RuntimeError("WebSocket receive loop terminated")
                )
            self._pending.clear()

        self._ws = None


# ============================================================
# Internal Support Types
# ============================================================

@dataclass
class _PendingRequest:
    response: Optional[dict] = None
    error: Optional[Exception] = None

    def __post_init__(self) -> None:
        self.event = threading.Event()

    def finish(
        self,
        response: Optional[dict] = None,
        error: Optional[Exception] = None,
    ) -> None:
        self.response = response
        self.error = error
        self.event.set()
