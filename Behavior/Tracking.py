import threading
from Motion.Move import Move
from Motion.Wait import wait_for_complete
from Motion.Limits import Limits
from Motion.Position import get_motor_positions

# ---------------- CONFIG ----------------
GAIN_MM_PER_PX = 0.0030
DEADZONE_PX = 15
MAX_STEP_MM = 1.0
TRACK_SPEED = 800
# ---------------------------------------

class _TrackState:
    def __init__(self):
        self.error_history = []

_state = _TrackState()

def reset_tracking():
    """Call once when entering TRACK mode."""
    _state.error_history.clear()

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

    # --- Get current position ---
    try:
        pos = get_motor_positions()
        if not pos or 'z' not in pos:
            print("Could not get current Z position.")
            return
        current_z = float(pos['z'])
    except Exception as e:
        print(f"Error getting motor positions: {e}")
        return

    # --- Compute relative Z correction ---
    dz = error_px * GAIN_MM_PER_PX

    # Clamp step
    if dz > 0:
        dz = min(MAX_STEP_MM, dz)
    else:
        dz = max(-MAX_STEP_MM, dz)

    # Clamp against limits
    if current_z + dz > Limits.Z_MAX:
        dz = Limits.Z_MAX - current_z
    elif current_z + dz < Limits.Z_MIN:
        dz = Limits.Z_MIN - current_z

    if abs(dz) < 0.001:  # No significant move
        return

    # --- Deterministic motion ---
    Move(z=dz, speed=TRACK_SPEED)
    wait_for_complete()

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
