import threading
from Motion.Move import Move
from Motion.Wait import wait_for_complete
from Motion.Limits import Limits

# ---------------- CONFIG ----------------
GAIN_MM_PER_PX = 0.0030
DEADZONE_PX = 15
MAX_STEP_MM = 1.0
TRACK_SPEED = 800
# ---------------------------------------

class _TrackState:
    def __init__(self):
        self.current_z = 10.0
        self.error_history = []


_state = _TrackState()


def reset_tracking(z_start=None):
    """Call once when entering TRACK mode."""
    _state.error_history.clear()
    if z_start is not None:
        _state.current_z = z_start


def track(cx, frame_width):
    state = _state

    # --- Smooth error ---
    state.error_history.append(cx)
    if len(state.error_history) > 3:
        state.error_history.pop(0)

    smoothed_cx = sum(state.error_history) / len(state.error_history)

    center_x = frame_width / 2.0
    error_px = smoothed_cx - center_x

    # --- Deadzone ---
    if abs(error_px) < DEADZONE_PX:
        return

    # --- Compute relative Z correction ---
    dz = error_px * GAIN_MM_PER_PX

    # Clamp step
    if dz > 0:
        dz = min(MAX_STEP_MM, dz)
    else:
        dz = max(-MAX_STEP_MM, dz)

    # Clamp against limits
    if state.current_z + dz > Limits.Z_MAX:
        dz = Limits.Z_MAX - state.current_z
    elif state.current_z + dz < Limits.Z_MIN:
        dz = Limits.Z_MIN - state.current_z

    if dz == 0:
        return

    # --- Deterministic motion ---
    Move(z=dz, speed=TRACK_SPEED)
    wait_for_complete()

    # --- Update mechanical truth ---
    state.current_z += dz


class TrackThread(threading.Thread):
    def __init__(self, cx, frame_width, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self.cx = cx
        self.frame_width = frame_width
        self._stop_event = threading.Event()

    def run(self):
        """Main loop for the tracking thread."""
        print("Track thread started.")
        while not self._stop_event.is_set():
            track(self.cx, self.frame_width)
        print("Track thread stopped.")

    def stop(self):
        """Signals the thread to stop."""
        self._stop_event.set()

    def update_center(self, cx):
        self.cx = cx
