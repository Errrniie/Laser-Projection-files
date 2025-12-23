import threading
from Motion.Move import Move
from Motion.Wait import wait_for_complete
from Motion.Limits import Limits
from Motion.Position import get_motor_positions
from Motion.Moonraker_ws import MoonrakerWSClient


class _PanState:
    def __init__(self):
        self.z_direction = 1  # +1 up, -1 down

_pan_state = _PanState()

PAN_STEP = 1
SEARCH_SPEED = 400

def pan_z(ws_client: MoonrakerWSClient):
    """
    Performs one step of the pan search.
    Blocks until motion completes.
    """
    state = _pan_state
    try:
        pos = get_motor_positions(ws_client)
        if not pos or 'z' not in pos:
            print("Could not get current Z position.")
            return
        current_z = float(pos['z'])
    except Exception as e:
        print(f"Error getting motor positions: {e}")
        return

    next_dz = state.z_direction * PAN_STEP
    predicted_z = current_z + next_dz

    if predicted_z > Limits.Z_MAX or predicted_z < Limits.Z_MIN:
        state.z_direction *= -1
    
    dz = state.z_direction * PAN_STEP

    final_z = current_z + dz
    if final_z > Limits.Z_MAX:
        dz = Limits.Z_MAX - current_z
    elif final_z < Limits.Z_MIN:
        dz = Limits.Z_MIN - current_z

    if abs(dz) < 0.001:
        return

    Move(ws_client, z=dz, speed=SEARCH_SPEED)
    wait_for_complete(ws_client)

class SearchThread(threading.Thread):
    def __init__(self, ws_client: MoonrakerWSClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self._stop_event = threading.Event()
        self._ws_client = ws_client

    def run(self):
        """Main loop for the search thread."""
        print("Search thread started.")
        while not self._stop_event.is_set():
            pan_z(self._ws_client)
        print("Search thread stopped.")

    def stop(self):
        """Signals the thread to stop."""
        self._stop_event.set()
