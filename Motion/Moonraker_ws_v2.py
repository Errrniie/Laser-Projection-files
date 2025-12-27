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

        # Toolhead timing cache
        self._toolhead_print_time: Optional[float] = None
        self._toolhead_estimated_print_time: Optional[float] = None
        self._motion_queue_empty: Optional[bool] = None
        self._motion_epsilon: float = 1e-3

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
            # Fetch initial printer state to seed print_stats, idle_timeout, and toolhead timing
            resp = self.call(
                "printer.objects.query",
                {
                    "objects": {
                        "print_stats": None,
                        "idle_timeout": ["state", "printing_time"],
                        "toolhead": ["print_time", "estimated_print_time"],
                    }
                },
                timeout_s=2.0,
            )
            status = resp.get("result", {}).get("status", {})
            if status:
                with self._cache_lock:
                    self._printer_state.update(status)
                    self._printer_status_time = time.time()
                    self._refresh_motion_queue_state()
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
        """
        Return True if printer is idle (not executing G-code), False if busy,
        or None if state is unknown.
        
        Checks idle_timeout.state for actual G-code execution status.
        """
        with self._cache_lock:
            # Check idle_timeout.state - this is the reliable indicator
            idle_timeout = self._printer_state.get("idle_timeout")
            if isinstance(idle_timeout, dict):
                state = idle_timeout.get("state")
                if isinstance(state, str):
                    state_lower = state.lower()
                    if state_lower in ("idle", "ready"):
                        return True
                    if state_lower == "printing":
                        return False
            
            # Fallback to print_stats if idle_timeout.state not available
            print_stats = self._printer_state.get("print_stats")
            if isinstance(print_stats, dict):
                status = print_stats.get("state")
                if isinstance(status, str):
                    status_lower = status.lower()
                    if status_lower in ("standby", "ready", "complete"):
                        return True
                    if status_lower in ("printing", "paused"):
                        return False
            
            return None

    @property
    def estimated_print_time(self) -> Optional[float]:
        """Return toolhead.estimated_print_time, or None if not available."""
        with self._cache_lock:
            toolhead = self._printer_state.get("toolhead")
            if isinstance(toolhead, dict):
                ept = toolhead.get("estimated_print_time")
                if isinstance(ept, (int, float)):
                    return float(ept)
            return None

    @property
    def motion_queue_empty(self) -> Optional[bool]:
        """Return True when (estimated_print_time - print_time) <= epsilon, else False/None."""
        with self._cache_lock:
            return self._motion_queue_empty

    @property
    def queue_depth(self) -> Optional[float]:
        """Return (estimated_print_time - print_time) in seconds, or None if unknown."""
        with self._cache_lock:
            if self._toolhead_print_time is not None and self._toolhead_estimated_print_time is not None:
                diff = self._toolhead_estimated_print_time - self._toolhead_print_time
                return diff
            return None

    def _update_printer_state(self, notification: dict) -> None:
        params = notification.get("params")
        if not isinstance(params, list) or not params:
            return
        if not isinstance(params[0], dict):
            return

        incoming = params[0]

        with self._cache_lock:
            # Debug log of raw toolhead payload (single line to reduce spam)
            if "toolhead" in incoming:
                try:
                    print(
                        "[MoonrakerWS] toolhead notify",
                        json.dumps(incoming.get("toolhead", {}), sort_keys=True),
                    )
                except Exception:
                    pass

            # Merge top-level state, with deep merge for toolhead to avoid losing fields
            for key, value in incoming.items():
                if key == "toolhead" and isinstance(value, dict):
                    existing = self._printer_state.get("toolhead")
                    if isinstance(existing, dict):
                        merged = existing.copy()
                        merged.update(value)
                        self._printer_state["toolhead"] = merged
                    else:
                        self._printer_state["toolhead"] = value
                else:
                    self._printer_state[key] = value

            self._printer_status_time = time.time()
            self._refresh_motion_queue_state()

    def _refresh_motion_queue_state(self) -> None:
        toolhead = self._printer_state.get("toolhead")
        if isinstance(toolhead, dict):
            raw_pt = toolhead.get("print_time")
            raw_ept = toolhead.get("estimated_print_time")
            if isinstance(raw_pt, (int, float)):
                self._toolhead_print_time = float(raw_pt)
            if isinstance(raw_ept, (int, float)):
                self._toolhead_estimated_print_time = float(raw_ept)

        pt = self._toolhead_print_time
        ept = self._toolhead_estimated_print_time

        if pt is None or ept is None:
            # Unknown until both are seen at least once
            self._motion_queue_empty = None
            return

        diff = ept - pt
        # Queue is busy only when estimated_print_time is significantly ahead of print_time
        # Negative diff (print_time > estimated) is an async update artifact, treat as empty
        if diff > self._motion_epsilon:
            self._motion_queue_empty = False
        else:
            self._motion_queue_empty = True

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
