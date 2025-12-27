from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, Union
import threading

# Only permitted public class
class MotionController:
    """
    Pure motion execution layer for Moonraker. Receives high-level intent,
    computes safe G-code, and prevents overlapping hardware motion.
    Never makes behavior or timing decisions. Threadsafe for Main polling.
    """
    def __init__(self, moonraker: Any, config: Dict[str, Any]):
        """
        moonraker : MoonrakerWSClient (not checked here)
        config: dict with axis limits, neutral pose, speeds:
            {
                "limits": {"x": [min, max], "y": [min, max], "z": [min, max]},
                "neutral": {"x": float, "y": float, "z": float},
                "speeds": {"travel": float, "z": float}
            }
        """
        self._client = moonraker
        self._limits = config.get("limits", {})
        self._neutral = config.get("neutral", {})
        self._speeds = config.get("speeds", {})
        self._lock = threading.Lock()

        # Internal current intent; None means unset/no change
        self._intent: Dict[str, Optional[float]] = {"x": None, "y": None, "z": None}
        # Last target actually sent
        self._last_sent: Dict[str, Optional[float]] = {"x": None, "y": None, "z": None}

        # Motion-in-flight latch
        self._motion_in_flight = False   
        self._awaiting_busy = False

    # -- Intent Setting --

    def set_intent(self, *, x: Optional[float]=None, y: Optional[float]=None, z: Optional[float]=None) -> None:
        """
        Non-blocking, overwrite previous intent for given axes.
        Unspecified axes are not affected.
        Does not emit or block or validate.
        """
        with self._lock:
            if x is not None:
                self._intent["x"] = x
            if y is not None:
                self._intent["y"] = y
            if z is not None:
                self._intent["z"] = z

    def set_neutral_intent(self) -> None:
        """Set intent to neutral pose (does not block, does not emit)."""
        with self._lock:
            for axis in ("x", "y", "z"):
                val = self._neutral.get(axis)
                if val is not None:
                    self._intent[axis] = val

    # -- Motion Execution (Main-driven, safe to call every frame) --
    def update(self) -> None:
        """
        Examines current intent vs. last-sent, clamps as needed,
        emits minimal required G-code to _client, and updates last_sent.
        Skips motion if printer is busy or no motion is pending.
        Does not block.
        """
        with self._lock:
            
                        # If a motion is in flight
            if self._motion_in_flight:
                idle = self._client.is_idle
                if idle is False:
                    self._awaiting_busy = False  # busy observed, keep latch set
                    return
                if idle is True and not self._awaiting_busy:
                    self._motion_in_flight = False  # busy phase finished
                return

            # Only send a move if no motion is in flight and Moonraker reports idle
            idle = self._client.is_idle
            if idle is not True:
                return

            # Get snapshot of intent and last sent
            tgt = self._intent.copy()
            prev = self._last_sent.copy()

            # Find which axes have new intent we haven't sent
            move_axes = {a: tgt[a] for a in ("x", "y", "z") if tgt[a] is not None and tgt[a] != prev[a]}
            if not move_axes:
                return  # No new motion intent

            # Clamp and build G-code
            clamped = {}
            for axis, val in move_axes.items():
                lo, hi = self._limits.get(axis, (None, None))
                v = float(val)
            if lo is not None:
                v = max(lo, v)
            if hi is not None:
                v = min(hi, v)
            clamped[axis] = v

            # Construct G-code in absolute mode
            abs_x = clamped.get("x", self._last_sent["x"])
            abs_y = clamped.get("y", self._last_sent["y"])
            abs_z = clamped.get("z", self._last_sent["z"])
            f = self._speeds["z"] if (abs_z is not None and (abs_x is None or abs_x == self._last_sent["x"]) and (abs_y is None or abs_y == self._last_sent["y"])) else self._speeds["travel"]
            
            parts = []
            if abs_x is not None:
                parts.append(f"x={abs_x:.2f}")
            if abs_y is not None:
                parts.append(f"y={abs_y:.2f}")
            if abs_z is not None:
                parts.append(f"z={abs_z:.2f}")
                
            cmd = f"MOVE {' '.join(parts)} SPEED={f:.0f}"

            self._client.send_gcode(cmd)
            print(f"[MotionController] Sent G-code: {cmd}")
            
            # Mark motion as in flight
            self._motion_in_flight = True
            self._awaiting_busy = True
            # Update last_sent for moved axes ONLY
            
            for axis in clamped:
                self._last_sent[axis] = clamped[axis]
                self._intent[axis] = None

                

    # -- Optional blocking call (explicit use only; never for SEARCH or TRACK) --

    def move_blocking(self, timeout: float = 10.0) -> bool:
        """
        Emit pending motion, then (optionally) wait until printer reports idle.
        Never called except by higher layers for INIT/SHUTDOWN.
        Returns True if idle reached, else False on timeout.
        """
        self.update()

    # Block only if Moonraker supports it
        if hasattr(self._client, "wait_until_idle"):
            try:
                return bool(self._client.wait_until_idle(timeout_s=timeout))
            except Exception:
                return False

        return False

    # -- Safe state helpers --

    @property
    def target_intent(self) -> Dict[str, Optional[float]]:
        """Snapshot copy of current intent."""
        with self._lock:
            return self._intent.copy()

    @property
    def last_sent_target(self) -> Dict[str, Optional[float]]:
        """Snapshot copy of last-sent, for debug."""
        with self._lock:
            return self._last_sent.copy()
        
    