import threading
from Motion.Move import safe_move
from Motion.Moonraker_ws import MoonrakerWSClient
from Behavior.MotionGate import motion_in_flight
import time

# --- PID Controller Constants ---
Kp = 0.003 
Ki = 0.000
Kd = 0.000
TRACKING_SPEED = 800
DEADZONE = 15
LOOP_INTERVAL = 0.025  # 25ms, which is 40Hz

def reset_tracking(z_start=None):
    """Resets tracking-related state if needed in the future."""
    print("Tracking state is managed by TrackThread instances.")

class TrackThread(threading.Thread):
    def __init__(self, cx, frame_width, ws_client: MoonrakerWSClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self._stop_event = threading.Event()
        self._ws_client = ws_client

        self._lock = threading.Lock()
        self._target_cx = cx
        self._frame_width = frame_width
        
        self.last_error = 0
        self.integral = 0

    def run(self):
        """
        Main tracking loop. This runs in a separate thread.
        """
        print("Track thread started.")
        while not self._stop_event.is_set():
            loop_start_time = time.time()

            with self._lock:
                current_cx = self._target_cx
            
            self.track(current_cx)

            elapsed_time = time.time() - loop_start_time
            sleep_time = LOOP_INTERVAL - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        print("Track thread stopped.")

    def track(self, cx):
        """
        Calculates and executes a single motor movement step based on PID logic.
        It respects the motion gate, dropping corrections if a move is in flight.
        """
        # If a move is already in progress, drop this correction and wait for the next cycle.
        if motion_in_flight.is_set():
            return

        center_x = self._frame_width / 2
        error = cx - center_x

        if abs(error) < DEADZONE:
            self.integral = 0 # Reset integral when in deadzone
            return

        self.integral += error
        derivative = error - self.last_error

        output = Kp * error + Ki * self.integral + Kd * derivative
        self.last_error = error

        # Clamp the output to a reasonable range for movement
        dz = max(-1.0, min(1.0, output))

        # Safely move the motor using the motion gate
        safe_move(self._ws_client, z=dz, speed=TRACKING_SPEED)

    def update_center(self, cx):
        """
        Update the target center position from the main thread.
        """
        with self._lock:
            self._target_cx = cx

    def stop(self):
        """Signals the thread to stop."""
        self._stop_event.set()
