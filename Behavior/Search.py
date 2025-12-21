STEP_MM = 0.4
SEARCH_SPEED = 300  # slow, safe

Z_MIN = 0.0
Z_MAX = 20.0

_current_z = 10.0
_dir = -1


def pan_z_step():
    global _current_z, _dir

    next_z = _current_z + _dir * STEP_MM

    if next_z <= Z_MIN:
        next_z = Z_MIN
        _dir = +1
    elif next_z >= Z_MAX:
        next_z = Z_MAX
        _dir = -1

    # issue ONE deterministic move
    move_all(z=next_z - _current_z, speed=SEARCH_SPEED)
    wait_for_complete()

    # now it is safe to update state
    _current_z = next_z
