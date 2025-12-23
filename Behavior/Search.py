import threading
import time
from Motion.Move import safe_move_and_wait
from Motion.Position import get_motor_positions
from Motion.Moonraker_ws import MoonrakerWSClient

# --- Search Constants ---
SEARCH_EXTENT_MM = 10  # How far to move from the last known position
SEARCH_SPEED = 50
LOOP_INTERVAL = 0.1

class SearchThread(threading.Thread):
    def __init__(self, ws_client: MoonrakerWSClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self._stop_event = threading.Event()
        self._ws_client = ws_client

    def run(self):
        """
        Main searching loop.
        Scans locally around the last known Z position.
        """
        print("Search thread started.")
        
        # Get the Z position where the target was lost
        try:
            pos = get_motor_positions(self._ws_client)
            if pos is None:
                raise RuntimeError("Could not get current position to start search.")
            start_z = pos['z_raw']
            print(f"Starting local search around Z={start_z:.2f}mm")
        except Exception as e:
            print(f"Error starting search: {e}. Aborting search thread.")
            return

        # The search pattern will be: start -> start-extent -> start+extent -> start
        search_points = [
            start_z - SEARCH_EXTENT_MM,
            start_z + SEARCH_EXTENT_MM,
            start_z
        ]

        for target_z in search_points:
            # If a stop is requested during the search sequence, exit immediately.
            if self._stop_event.is_set():
                print("Search cancelled.")
                break
            
            try:
                print(f"Searching... moving to Z={target_z:.2f}")
                safe_move_and_wait(self._ws_client, z=target_z, speed=SEARCH_SPEED)
            except Exception as e:
                print(f"Error in search loop: {e}. Stopping search.")
                self._stop_event.set()
                break # Exit the loop on error

        # If the loop completes without being stopped, it means the target was not found.
        if not self._stop_event.is_set():
            print("Local search finished, target not re-acquired.")
        
        print("Search thread stopped.")

    def stop(self):
        """Signals the thread to stop."""
        self._stop_event.set()
