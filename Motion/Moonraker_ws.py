# GooseProject/Motion/moonraker_ws.py
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import websocket  # websocket-client

# --- Constants ---
RECONNECT_INTERVAL_S = 3.0

@dataclass
class _Pending:
    event: threading.Event
    resp: Optional[dict] = None
    err: Optional[Exception] = None


class MoonrakerWSClient:
    """
    Manages a WebSocket connection to Moonraker, handling JSON-RPC requests,
    notifications, and automatic reconnection. It is thread-safe.
    """

    def __init__(self, ws_url: str, recv_timeout_s: float = 0.25):
        self.ws_url = ws_url
        self.recv_timeout_s = recv_timeout_s

        self._ws: Optional[websocket.WebSocket] = None
        self._rx_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

        self._send_lock = threading.Lock()
        self._pending_lock = threading.Lock()
        self._pending: Dict[int, _Pending] = {}
        self._next_id = 1

        self._notif_handlers: Dict[str, Callable[[dict], None]] = {}
        
        self._connection_lock = threading.Lock()
        self._last_connect_attempt = 0

    def connect(self) -> None:
        """
        Establishes the WebSocket connection if not already connected.
        This method is thread-safe and rate-limited.
        """
        with self._connection_lock:
            if self.is_connected():
                                           return
            
            # Rate-limit connection attempts
            if time.time() - self._last_connect_attempt < RECONNECT_INTERVAL_S:
                return

            self._last_connect_attempt = time.time()
            self.close() # Ensure everything is clean before starting
            self._stop.clear()

            try:
                print("Connecting to Moonraker...")
                self._ws = websocket.create_connection(self.ws_url, timeout=5)
                self._ws.settimeout(self.recv_timeout_s)
                
                self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
                self._rx_thread.start()
                print("Moonraker connection established.")
            except (websocket.WebSocketException, ConnectionRefusedError, OSError) as e:
                print(f"Failed to connect to Moonraker: {e}")
                self._ws = None # Ensure ws is None on failure

    def is_connected(self) -> bool:
        """Checks if the WebSocket is connected and the reader thread is active."""
        return self._ws is not None and self._rx_thread is not None and self._rx_thread.is_alive()

    def close(self) -> None:
        """Closes the WebSocket connection and cleans up resources."""
        if self._stop.is_set():
            return # Already closing/closed
        
        self._stop.set()
        
        ws = self._ws
        self._ws = None

        if ws:
            try:
                ws.close()
            except Exception:
                pass
        
        if self._rx_thread and threading.current_thread() != self._rx_thread:
            self._rx_thread.join(timeout=2.0)

        # Fail any pending requests
        with self._pending_lock:
            for p in self._pending.values():
                p.err = RuntimeError("WebSocket closed")
                p.event.set()
            self._pending.clear()

    def on_notify(self, method: str, handler: Callable[[dict], None]) -> None:
        """Register a handler for notifications with a given method name."""
        self._notif_handlers[method] = handler

    def call(self, method: str, params: Optional[dict] = None, timeout_s: float = 2.0) -> dict:
        """
        Sends a JSON-RPC request and waits for a response.
        Handles reconnection if the connection is down.
        """
        if not self.is_connected():
            self.connect()
            if not self.is_connected():
                raise RuntimeError("WebSocket not connected")

        req_id = self._alloc_id()
        msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            msg["params"] = params

        pending = _Pending(event=threading.Event())
        with self._pending_lock:
            self._pending[req_id] = pending

        payload = json.dumps(msg)

        try:
            with self._send_lock:
                if self._ws:
                    self._ws.send(payload)
                else:
                    raise websocket.WebSocketConnectionClosedException("WebSocket is None")
        except (websocket.WebSocketConnectionClosedException, AttributeError) as e:
            # Connection dropped, pop pending and raise
            self._pop_pending(req_id, err=e)
            self.close() # Trigger a clean close and allow reconnection on next call
            raise RuntimeError("WebSocket not connected") from e

        if not pending.event.wait(timeout_s):
            self._pop_pending(req_id, err=TimeoutError(f"Timeout waiting for {method}"))
            raise TimeoutError(f"Moonraker WS call timeout: {method}")

        if pending.err:
            raise pending.err
        
        assert pending.resp is not None
        return pending.resp

    def _alloc_id(self) -> int:
        with self._pending_lock:
            req_id = self._next_id
            self._next_id += 1
        return req_id

    def _pop_pending(self, req_id: int, err: Optional[Exception] = None, resp: Optional[dict] = None) -> None:
        with self._pending_lock:
            p = self._pending.pop(req_id, None)
        if p:
            p.err = err
            p.resp = resp
            p.event.set()

    def _rx_loop(self) -> None:
        """The main loop for the reader thread."""
        while not self._stop.is_set():
            ws = self._ws
            if ws is None:
                break # Exit if connection is gone

            try:
                raw = ws.recv()
                if raw is None:
                    continue
            except websocket.WebSocketTimeoutException:
                continue
            except websocket.WebSocketConnectionClosedException:
                print("Moonraker connection closed.")
                self.close() # Trigger full cleanup
                return
            except Exception:
                # Be conservative: close so callers fail fast instead of hanging
                print("Error in WebSocket receive loop.")
                self.close()
                return

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            # Response to a request
            if isinstance(msg, dict) and "id" in msg:
                req_id = msg["id"]
                self._pop_pending(req_id, resp=msg)
                continue

            # Notification
            if isinstance(msg, dict) and "method" in msg:
                method = msg.get("method", "")
                handler = self._notif_handlers.get(method)
                if handler:
                    try:
                        handler(msg)
                    except Exception:
                        pass # Ignore errors in notification handlers
