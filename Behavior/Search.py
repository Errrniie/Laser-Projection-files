import threading
import time
from Motion.Move import safe_move, safe_move_and_wait
from Motion.Moonraker_ws import MoonrakerWSClient
import Motion.Limits as Limits
# --- Search Constants ---
SEARCH_EXTENT_MM = 15  # How far to move left/right from center in mm
SEARCH_SPEED = 500       # Speed for search movements
LOOP_INTERVAL = 0.1      # Seconds to wait between initiating search moves

SEARCH_MIN = -20
SEARCH_MAX = 20
SEARCH_STEP = 1
SEARCH_SPEED = 400
SEARCH_DWELL_S = 0.12 

class SearchThread(threading.Thread):
    def __init__(self, ws_client: MoonrakerWSClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self._stop_event = threading.Event()
        self._ws_client = ws_client
        self._search_direction = 1 # 1 for positive, -1 for negative
        self._first_step = True


    def run(self):
        print("Search thread started.")
        z = SEARCH_MIN
        direction = 1

        while not self._stop_event.is_set():
            if self._first_step:
    # First move after TRACK → SEARCH: do NOT block
                safe_move(self._ws_client, z=z, speed=SEARCH_SPEED)
                self._first_step = False
            else:
                # Normal serialized search steps
                safe_move_and_wait(self._ws_client, z=z, speed=SEARCH_SPEED)


            # Give vision time to see
            time.sleep(SEARCH_DWELL_S)

            if self._stop_event.is_set():
                break

            # Increment scan position
            z += direction * SEARCH_STEP

            # Reverse direction at bounds
            if z >= SEARCH_MAX:
                z = SEARCH_MAX
                direction = -1
            elif z <= SEARCH_MIN:
                z = SEARCH_MIN
                direction = 1

    print("Search thread stopped.")

    def stop(self):
        """Signals the thread to stop."""
        self._stop_event.set()
