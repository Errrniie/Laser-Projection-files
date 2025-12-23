# GooseProject/Motion/moonraker_ws.py
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import websocket  # websocket-client


@dataclass
class _Pending:
    event: threading.Event
    resp: Optional[dict] = None
    err: Optional[Exception] = None


class MoonrakerWSClient:
    """
    Single websocket connection + single reader thread.
    Thread-safe call() for JSON-RPC requests.
    Optional notification handlers for "method" messages.
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

    def connect(self) -> None:
        if self._ws is not None:
            return

        self._stop.clear()
        self._ws = websocket.create_connection(self.ws_url, timeout=5)
        self._ws.settimeout(self.recv_timeout_s)

        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start() 

    def is_connected(self) -> bool:
        return self._ws is not None

    def close(self) -> None:
        self._stop.set()

        ws = self._ws
        self._ws = None

        if ws:
            try:
                ws.close()
            except Exception:
                pass

        # fail any waiters
        with self._pending_lock:
            for p in self._pending.values():
                p.err = RuntimeError("WebSocket closed")
                p.event.set()
            self._pending.clear()

    def on_notify(self, method: str, handler: Callable[[dict], None]) -> None:
        """Register handler for notifications with a given method name."""
        self._notif_handlers[method] = handler

    def call(self, method: str, params: Optional[dict] = None, timeout_s: float = 2.0) -> dict:
        """JSON-RPC call. Returns the full response dict."""
        if self._ws is None:
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
                self._ws.send(payload)
        except Exception as e:
            self._pop_pending(req_id, err=e)
            raise

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
        while not self._stop.is_set():
            ws = self._ws
            if ws is None:
                break

            try:
                raw = ws.recv()
                if raw is None:
                    continue
            except websocket.WebSocketTimeoutException:
                continue
            except websocket.WebSocketConnectionClosedException as e:
                self.close()
                return
            except Exception as e:
                # conservative: close so callers fail fast instead of hanging
                self.close()
                return

            try:
                msg = json.loads(raw)
            except Exception:
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
                        pass
