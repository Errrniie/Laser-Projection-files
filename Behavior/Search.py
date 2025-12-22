from Motion.Move import Move
from Motion.Wait import wait_for_complete
from Motion.Limits import Limits


class _PanState:
    def __init__(self):
        self.current_z = 10.0
        self.z_direction = 1  # +1 up, -1 down


_pan_state = _PanState()

PAN_STEP = 2        # mm (small = controllable)
SEARCH_SPEED = 800    # mm/min


def pan_z():
    """
    Deterministic Z-axis search step.
    Blocks until motion completes.
    Safe to interrupt at any time.
    """
    state = _pan_state

    # Reverse direction at limits
    if state.current_z >= Limits.Z_MAX:
        state.z_direction = -1
    elif state.current_z <= Limits.Z_MIN:
        state.z_direction = 1

    dz = state.z_direction * PAN_STEP

    # Clamp so we never exceed limits
    if state.current_z + dz > Limits.Z_MAX:
        dz = Limits.Z_MAX - state.current_z
    elif state.current_z + dz < Limits.Z_MIN:
        dz = Limits.Z_MIN - state.current_z

    # If no movement possible, flip direction and exit
    if dz == 0:
        state.z_direction *= -1
        return

    # --- Deterministic motion ---
    Move(z=dz, speed=SEARCH_SPEED)
    wait_for_complete()

    # Update confirmed mechanical state
    state.current_z += dz
