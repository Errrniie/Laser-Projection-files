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

    def go_intent(self) -> None:
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
            # Get snapshot of intent and last sent
            tgt = self._intent.copy()
            prev = self._last_sent.copy()
            # Find which axes have new intent we haven't sent
            move_axes = {a: tgt[a] for a in ("x", "y", "z") if tgt[a] is not None and tgt[a] != prev[a]}
            if not move_axes:
                return  # No new motion intent

            # Check hardware status non-blocking
            idle = self._client.is_idle
            if idle is not True:
                 return


            # Clamp and build G-code
            clamped: Dict[str, float] = {}
            for axis, val in move_axes.items():
                l = self._limits.get(axis)
                v = float(val)
                if l and isinstance(l, (list, tuple)) and len(l) == 2:
                    v = min(max(v, l[0]), l[1])
                clamped[axis] = v

            if not clamped:
                return  # No valid motion required

            # Construct G-code in absolute mode
            gcode = ["G90"]  # Absolute positioning is enforced
            move_cmds = []   # G1 X.. Y.. Z.. F..
            xyz = [clamped.get(a, None) for a in ("x", "y", "z") if a in clamped]
            # For Z-only, X/Y-only, or combined:
            g1 = "G1"
            for axis in ("x", "y", "z"):
                if axis in clamped:
                    g1 += f" {axis.upper()}{clamped[axis]:.5f}"

            # Set feedrate
            f = None
            if "z" in clamped and not ("x" in clamped or "y" in clamped):
                f = self._speeds.get("z")
            else:
                f = self._speeds.get("travel")
            if f is not None:
                g1 += f" F{f:.0f}"

            gcode.append(g1)
            # Fire-and-forget (do not block, do not wait)
            self._client.send_gcode("\n".join(gcode))

            # Update last_sent for moved axes ONLY
            for axis in clamped:
                self._last_sent[axis] = clamped[axis]
            # Unset only the motion that was just sent; intention is single-writer
            # Clear consumed intent so motion is edge-triggered, not level-triggered
            for axis in clamped:
                self._intent[axis] = None

    def home(self, timeout: float = 30.0) -> None:
        """
        Perform a full homing cycle.
        Blocking. Explicit use only (INIT / SHUTDOWN).
        """
        # Send homing command
        self._client.call(
            "printer.gcode.script",
            {"script": "G28"},
            timeout_s=timeout
    )

    # Optionally wait until idle for safety
        if hasattr(self._client, "wait_until_idle"):
            ok = self._client.wait_until_idle(timeout_s=timeout)
            if not ok:
                raise RuntimeError("Homing completed but printer did not return to idle")


    # -- Optional blocking call (explicit use only; never for SEARCH or TRACK) --

    def move_blocking(self, timeout: float = 10.0) -> bool:
        """
        Emit pending motion, then (optionally) wait until printer reports idle.
        Never called except by higher layers for INIT/SHUTDOWN.
        Returns True if idle reached, else False on timeout.
        """
        self.emit_motion()
        if hasattr(self._client, "wait_until_idle"):
            try:
                # Wait (blocking), don't loop forever, surface errors upward
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
        
    