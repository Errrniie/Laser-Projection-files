from Motion.Move import move_all
from Motion.Wait import wait_for_complete
from Motion.Limits import Limits


class _PanState:
    def __init__(self):
        self.current_z = Limits.Z_MIN
        self.z_direction = 1  # +1 = up, -1 = down


_pan_state = _PanState()

PAN_STEP = 0.5  # mm


def pan_z():
    state = _pan_state

    # Reverse at limits
    if state.current_z >= Limits.Z_MAX:
        state.z_direction = -1
    elif state.current_z <= Limits.Z_MIN:
        state.z_direction = 1

    dz = state.z_direction * PAN_STEP

    # Clamp step so we never cross limits
    if state.current_z + dz > Limits.Z_MAX:
        dz = Limits.Z_MAX - state.current_z
    elif state.current_z + dz < Limits.Z_MIN:
        dz = Limits.Z_MIN - state.current_z

    # Issue ONE relative move
    move_all(z=dz, speed=500)
    wait_for_complete()

    # Update mechanical truth AFTER motion finishes
    state.current_z += dz
