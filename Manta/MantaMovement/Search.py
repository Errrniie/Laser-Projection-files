import time
import requests

MANTA_IP = "192.168.8.127"

Z_MIN = 0.0
Z_MAX = 20.0

STEP_MM = 0.4           # larger step → smoother
FEEDRATE = 150          # mm/min (slow sweep)
UPDATE_HZ = 25           # how often we stream moves

_dt = 1.0 / UPDATE_HZ
_last = 0.0

_current_z = 10.0
_dir = -1


def _send_gcode(script: str):
    try:
        requests.post(
            f"http://{MANTA_IP}/printer/gcode/script",
            json={"script": script},
            timeout=0.15
        )
    except requests.exceptions.RequestException:
        pass


def pan_z():
    """
    Continuous, interruptible pan.
    """
    global _current_z, _dir, _last

    now = time.time()
    if now - _last < _dt:
        return

    next_z = _current_z + _dir * STEP_MM

    if next_z <= Z_MIN:
        next_z = Z_MIN
        _dir = +1
    elif next_z >= Z_MAX:
        next_z = Z_MAX
        _dir = -1

    gcode = f"G1 Z{next_z:.3f} F{FEEDRATE}"
    _send_gcode(gcode)

    _current_z = next_z
    _last = now


def get_current_z():
    return _current_z


def set_current_z(z):
    global _current_z
    _current_z = z
