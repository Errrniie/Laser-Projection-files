from __future__ import annotations
from Motion.Moonraker_ws import MoonrakerWSClient
from Behavior.MotionGate import motion_lock, motion_in_flight
from Motion.Wait import wait_for_complete

def safe_move(dx, dz):
    if motion_in_flight.is_set():
        return False  # drop this correction

    with motion_lock:
        motion_in_flight.set()
        Move(dx=dx, dz=dz)
    return True

def wait_and_release(timeout=1.0):
    wait_for_complete(timeout)
    motion_in_flight.clear()

def Move(ws_client: MoonrakerWSClient, x: float | None = None, y: float | None = None, z: float | None = None, speed: int = 1200):
    """Sends a relative move command to the printer."""
    parts = []

    if x is not None:
        parts.append(f"X={x:.4f}")
    if y is not None:
        parts.append(f"Y={y:.4f}")
    if z is not None:
        parts.append(f"Z={z:.4f}")

    if not parts:
        return  # No move to make

    parts.append(f"SPEED={speed}")

    cmd = "MOVE " + " ".join(parts)

    print("Sending:", cmd)
    ws_client.call(
        "printer.gcode.script",
        {"script": cmd},
    )
