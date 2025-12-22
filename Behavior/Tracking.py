import time
import requests

# ---------------- CONFIG ----------------
MANTA_IP = "192.168.8.127"

Z_MIN = 0.0
Z_MAX = 20.0

GAIN_MM_PER_PX = 0.0030
DEADZONE_PX = 15
MAX_STEP_MM = 0.8
FEEDRATE = 600
UPDATE_HZ = 20

_dt = 1.0 / UPDATE_HZ
_last = 0.0
# ---------------------------------------

_current_z = 10.0
_error_history = []

def get_current_z():
    """Returns the last known Z position of the toolhead."""
    global _current_z
    return _current_z

def _send_gcode(script: str):
    try:
        requests.post(
            f"http://{MANTA_IP}/printer/gcode/script",
            json={"script": script},
            timeout=0.3
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
    
    _error_history.append(cx)
    if len(_error_history) > 3:
        _error_history.pop(0)
    
    smoothed_cx = sum(_error_history) / len(_error_history)
    
    center_x = frame_width / 2.0
    error_px = smoothed_cx - center_x
    
    if abs(error_px) < DEADZONE_PX:
        _last = now
        return
    
    dz = error_px * GAIN_MM_PER_PX
    
    if dz > 0:
        dz = min(MAX_STEP_MM, dz)
    else:
        dz = max(-MAX_STEP_MM, dz)
    
    next_z = _current_z + dz
    next_z = max(Z_MIN, min(Z_MAX, next_z))
    
    gcode = f"G1 Z{next_z:.3f} F{FEEDRATE}"
    _send_gcode(gcode)
    
    _current_z = next_z
    _last = now
