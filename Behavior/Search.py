import threading
from Motion.Move import safe_move_and_wait
from Motion.Moonraker_ws import MoonrakerWSClient

# --- Search Constants ---
SEARCH_SPEED = 50

class SearchThread(threading.Thread):
    def __init__(self, ws_client: MoonrakerWSClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self._stop_event = threading.Event()
        self._ws_client = ws_client

    def _move_and_check(self, z: int):
        """Helper function to perform a move and check for a stop signal."""
        # If a stop is requested before the move even starts, exit.
        if self._stop_event.is_set():
            return False

        print(f"Searching... moving to Z={z}mm")
        safe_move_and_wait(self._ws_client, z=z, speed=SEARCH_SPEED)
        
        # After the move, check again. This allows the search to be interrupted.
        if self._stop_event.is_set():
            return False
            
        return True

    def run(self):
        """
        Main searching loop.
        Scans in 1mm increments: 10->20, then 20->0, and repeats.
        The search is interruptible after each 1mm step.
        """
        print("Search thread started with incremental pattern.")

        try:
            # Loop the entire search pattern until explicitly stopped.
            while not self._stop_event.is_set():
                
                # --- Pattern Part 1: Move from 10mm to 20mm ---
                # We start at 10, so the first move is to 11.
                for target_z in range(11, 21): # Moves from 11, 12, ..., 20
                    if not self._move_and_check(target_z):
                        print("Search interrupted during 10->20 scan.")
                        return # Exit the run method completely

                # --- Pattern Part 2: Move from 20mm to 0mm ---
                for target_z in range(19, -1, -1): # Moves from 19, 18, ..., 0
                    if not self._move_and_check(target_z):
                        print("Search interrupted during 20->0 scan.")
                        return # Exit the run method completely
                
                # --- Pattern Part 3: Move from 0mm to 10mm to reset for next loop ---
                for target_z in range(1, 11): # Moves from 1, 2, ..., 10
                    if not self._move_and_check(target_z):
                        print("Search interrupted during 0->10 scan.")
                        return # Exit the run method completely

        except Exception as e:
            print(f"An error occurred in the incremental search loop: {e}")
        finally:
            self._stop_event.set()
            print("Search thread stopped.")

    def stop(self):
        """Signals the thread to stop immediately after its current 1mm move completes."""
        self._stop_event.set()
