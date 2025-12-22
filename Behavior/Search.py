import threading
from Motion.Move import Move
from Motion.Wait import wait_for_complete
from Motion.Limits import Limits


class _PanState:
    def __init__(self):
        self.current_z = 10.0
        self.z_direction = 1  # +1 up, -1 down


_pan_state = _PanState()

PAN_STEP = 1        # mm (small = controllable)
SEARCH_SPEED = 400    # mm/min


def get_current_z():
    """Returns the last known z-position from searching."""
    return _pan_state.current_z


def pan_z():
    """
    Performs one step of the pan search.
    Blocks until motion completes.
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


class SearchThread(threading.Thread):
    def __init__(self, z_start=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self._stop_event = threading.Event()
        if z_start is not None:
            _pan_state.current_z = z_start

    def _snap_to_grid(self):
        """Move to the nearest whole number to avoid getting stuck."""
        current_z = _pan_state.current_z
        rounded_z = round(current_z)

        if abs(current_z - rounded_z) > 0.01:  # Avoid tiny, unnecessary moves
            print(f"Snapping to grid: {current_z:.2f} -> {rounded_z}")
            Move(z=rounded_z - current_z, speed=SEARCH_SPEED)
            wait_for_complete()
            _pan_state.current_z = rounded_z

    def run(self):
        """Main loop for the search thread."""
        print("Search thread started.")
        while not self._stop_event.is_set():
            self._snap_to_grid()
            pan_z()
        print("Search thread stopped.")

    def stop(self):
        """Signals the thread to stop."""
        self._stop_event.set()
