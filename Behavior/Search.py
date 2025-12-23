import threading
import time
from Motion.Move import safe_move_and_wait
from Motion.Moonraker_ws import MoonrakerWSClient

# --- Search Constants ---
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
        Scans in a fixed absolute pattern: 10 -> 20 -> 0 -> 20 -> 0 ...
        """
        print("Search thread started.")

        # Define the repeating search pattern
        search_points = [20, 0]

        try:
            # 1. Initial move to the starting position
            print("Moving to search start position Z=10...")
            safe_move_and_wait(self._ws_client, z=10, speed=SEARCH_SPEED)

            # 2. Loop the search pattern until stopped
            while not self._stop_event.is_set():
                for target_z in search_points:
                    if self._stop_event.is_set():
                        break
                    
                    print(f"Searching... moving to Z={target_z}")
                    safe_move_and_wait(self._ws_client, z=target_z, speed=SEARCH_SPEED)
                    
                    # A short pause between moves
                    time.sleep(LOOP_INTERVAL)

        except Exception as e:
            print(f"Error in search loop: {e}. Stopping search.")
        finally:
            self._stop_event.set() # Ensure the thread stops on exit/error
            print("Search thread stopped.")

    def stop(self):
        """Signals the thread to stop."""
        self._stop_event.set()
