import threading
import time
from Motion.Move import safe_move_and_wait
from Motion.Moonraker_ws import MoonrakerWSClient

# --- Search Constants ---
SEARCH_EXTENT_MM = 15  # How far to move left/right from center in mm
SEARCH_SPEED = 500       # Speed for search movements
LOOP_INTERVAL = 0.1      # Seconds to wait between initiating search moves

class SearchThread(threading.Thread):
    def __init__(self, ws_client: MoonrakerWSClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self._stop_event = threading.Event()
        self._ws_client = ws_client
        self._search_direction = 1 # 1 for positive, -1 for negative

    def run(self):
        """
        Main searching loop.
        This runs in a separate thread and scans back and forth.
        """
        print("Search thread started.")
        while not self._stop_event.is_set():
            # Determine the target position for this part of the scan
            target_z = SEARCH_EXTENT_MM * self._search_direction
            
            # The safe_move_and_wait function handles the motion gate correctly.
            # It will acquire the lock, send the move, wait for completion, 
            # and release the lock.
            print(f"Searching... moving to Z={target_z}")
            safe_move_and_wait(self._ws_client, z=target_z, speed=SEARCH_SPEED)

            # Reverse direction for the next scan
            self._search_direction *= -1

            # If a stop is requested, exit immediately after the move completes.
            if self._stop_event.is_set():
                break
            
            # Wait a short moment before starting the next scan
            time.sleep(LOOP_INTERVAL)
        
        print("Search thread stopped.")

    def stop(self):
        """Signals the thread to stop."""
        self._stop_event.set()
