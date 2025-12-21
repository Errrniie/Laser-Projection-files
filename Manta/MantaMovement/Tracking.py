import time
import requests

# ---------------- CONFIG ----------------
MANTA_IP = "192.168.8.127"

Z_MIN = 0.0
Z_MAX = 20.0

GAIN_MM_PER_PX = 0.0030     # Increased slightly
DEADZONE_PX    = 15         # Increased for stability
MAX_STEP_MM    = 0.8        # Reduced for smoother moves
FEEDRATE       = 600        # Faster for quicker response
UPDATE_HZ      = 20         # SLOWER! Better for physical movement

_dt = 1.0 / UPDATE_HZ
_last = 0.0
# ---------------------------------------

_current_z = 10.0
_error_history = []  # For simple smoothing


def _send_gcode(script: str):
    try:
        requests.post(
            f"http://{MANTA_IP}/printer/gcode/script",
            json={"script": script},
            timeout=0.3  # Increased timeout
        )
    except requests.exceptions.RequestException:
        pass


def set_current_z(z):
    global _current_z
    _current_z = z


def track_z(cx, frame_width):
    global _current_z, _last
    
    now = time.time()
    if now - _last < _dt:
        return
    
    # Simple 3-frame moving average to reduce noise
    _error_history.append(cx)
    if len(_error_history) > 3:
        _error_history.pop(0)
    
    smoothed_cx = sum(_error_history) / len(_error_history)
    
    center_x = frame_width / 2.0
    error_px = smoothed_cx - center_x
    
    # Deadzone in pixels (easier to tune)
    if abs(error_px) < DEADZONE_PX:
        _last = now
        return
    
    # SIMPLE proportional control - remove nonlinear for now
    dz = error_px * GAIN_MM_PER_PX
    
    # Direction-aware clamping
    if dz > 0:
        dz = min(MAX_STEP_MM, dz)
    else:
        dz = max(-MAX_STEP_MM, dz)
    
    # Calculate next position
    next_z = _current_z + dz
    next_z = max(Z_MIN, min(Z_MAX, next_z))
    
    # Use ABSOLUTE positioning (G90) - more reliable
    gcode = f"G1 Z{next_z:.3f} F{FEEDRATE}"
    _send_gcode(gcode)
    
    _current_z = next_z
    _last = now