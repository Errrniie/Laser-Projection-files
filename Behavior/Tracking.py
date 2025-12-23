import threading
from Motion.Move import Move
from Motion.Position import get_motor_positions
import time

# --- Tracking State ---
class _TrackState:
    def __init__(self):
        self.last_error = 0
        self.integral = 0
        self.last_move_time = 0

_state = _TrackState()

def reset_tracking(z_start=None):
    """Resets the PID controller and tracking state."""
    _state.last_error = 0
    _state.integral = 0
    _state.last_move_time = 0
    print("Tracking state has been reset.")

# --- PID Controller ---
Kp = 0.014
Ki = 0.003
Kd = 0.005

MIN_MOVE_INTERVAL = 0.05  # 50ms
TRACKING_SPEED = 1200

def track(cx, frame_width):
    """
    Calculates the required motor movement to keep the target centered.
    This function should be called repeatedly with the latest center position.
    """
    current_time = time.time()
    if current_time - _state.last_move_time < MIN_MOVE_INTERVAL:
        return  # Don't move too frequently

    center_x = frame_width / 2
    error = cx - center_x

    # --- Deadzone: Ignore small errors ---
    if abs(error) < 15:
        return

    _state.integral += error
    derivative = error - _state.last_error

    # PID calculation
    output = Kp * error + Ki * _state.integral + Kd * derivative

    _state.last_error = error

    # Clamp the output to a reasonable range
    dz = max(-1.0, min(1.0, output))

    # Move the motor
    Move(z=dz, speed=TRACKING_SPEED)
    _state.last_move_time = current_time

# --- Tracking Thread ---
class TrackThread(threading.Thread):
    def __init__(self, cx, frame_width, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self.frame_width = frame_width
        self._stop_event = threading.Event()
        # Immediately perform the first track operation on creation
        self.update_center(cx)

    def run(self):
        """
        The tracking thread now does nothing in its main loop.
        The tracking logic is now driven by the main thread calling update_center.
        """
        print("Track thread started.")
        self._stop_event.wait()  # Stay alive until stop is called
        print("Track thread stopped.")

    def stop(self):
        """Signals the thread to stop."""
        self._stop_event.set()

    def update_center(self, cx):
        """
        This method is called from the main thread with new coordinates.
        It contains the call to the tracking logic.
        """
        if not self._stop_event.is_set():
            track(cx, self.frame_width)
