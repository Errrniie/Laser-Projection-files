import threading
import time

# --- Globals ---
_should_quit = threading.Event()

def should_quit():
    """Returns True if the user has requested to quit."""
    return _should_quit.is_set()

def _keyboard_listener():
    """Internal thread function to listen for keyboard input."""
    print("Keyboard listener started. Press 'q' to quit.")
    while not _should_quit.is_set():
        try:
            # This is a placeholder for a real key-listening library
            # In a real application, you'd use a library like 'pynput' or 'keyboard'
            # For this environment, we will simulate by checking for a file.
            with open('quit.txt', 'r') as f:
                if f.read().strip() == 'q':
                    print("'q' detected, signaling shutdown...")
                    _should_quit.set()
                    break
            time.sleep(0.5) # Check for the file every 500ms
        except FileNotFoundError:
            time.sleep(0.5)
        except Exception as e:
            print(f"Error in keyboard listener: {e}")
            break

class UserInputThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True

    def run(self):
        """Main loop for the user input thread."""
        _keyboard_listener()

    def stop(self):
        """Signals the thread to stop."""
        _should_quit.set()
