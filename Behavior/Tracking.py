import threading
from Motion.Move import Move
from Motion.Moonraker_ws import MoonrakerWSClient
import time

# --- PID Controller Constants ---
Kp = 0.003 
Ki = 0.000
Kd = 0.000
TRACKING_SPEED = 800
DEADZONE = 15
LOOP_INTERVAL = 0.025  # 50ms, which is 20Hz

def reset_tracking(z_start=None):
    """Resets tracking-related state if needed in the future."""
    # This function is now a placeholder, as the state is managed within the thread.
    print("Tracking state is managed by TrackThread instances.")

class TrackThread(threading.Thread):
    def __init__(self, cx, frame_width, ws_client: MoonrakerWSClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self._stop_event = threading.Event()
        self._ws_client = ws_client

        # --- Thread-safe tracking variables ---
        self._lock = threading.Lock()
        self._target_cx = cx
        self._frame_width = frame_width
        
        # --- PID state ---
        self.last_error = 0
        self.integral = 0

    def run(self):
        """
        Main tracking loop.
        This runs in a separate thread and does not block the main application.
        """
        print("Track thread started.")
        while not self._stop_event.is_set():
            loop_start_time = time.time()

            # --- Get the latest target position safely ---
            with self._lock:
                current_cx = self._target_cx
            
            # --- Perform tracking calculation ---
            self.track(current_cx)

            # --- Maintain a consistent loop rate ---
            elapsed_time = time.time() - loop_start_time
            sleep_time = LOOP_INTERVAL - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        print("Track thread stopped.")

    def track(self, cx):
        """
        Calculates and executes a single motor movement step based on PID logic.
        """
        center_x = self._frame_width / 2
        error = cx - center_x

        # --- Deadzone: Ignore small errors ---
        if abs(error) < DEADZONE:
            self.integral = 0 # Reset integral when in deadzone
            return

        self.integral += error
        derivative = error - self.last_error

        # PID calculation
        output = Kp * error + Ki * self.integral + Kd * derivative

        self.last_error = error

        # Clamp the output to a reasonable range for movement
        dz = max(-1.0, min(1.0, output))

        # Move the motor
        Move(self._ws_client, z=dz, speed=TRACKING_SPEED)

    def update_center(self, cx):
        """
        Update the target center position from the main thread.
        This is a non-blocking, thread-safe method.
        """
        with self._lock:
            self._target_cx = cx

    def stop(self):
        """Signals the thread to stop."""
        self._stop_event.set()
