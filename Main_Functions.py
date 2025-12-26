# --- Placeholder API for laser control ---
def laser_on():
    # Implement hardware-specific laser ON control here
    print("[LASER] ON")

def laser_off():
    # Implement hardware-specific laser OFF control here
    print("[LASER] OFF")

# --- Motion INTENT (non-blocking command) stub ---
def set_motion_intent(ws_client, z=None, mirror_angles=None):
    # Non-blocking: Send the latest Z or angle intent to Moonraker.
    # Real implementation should publish intent and return immediately.
    if z is not None:
        print(f"[MOTION INTENT] Z target: {z:.2f} mm")
    if mirror_angles is not None:
        print(f"[MOTION INTENT] Mirror angles: {mirror_angles}")

# --- Helper functions for state math (logic only, no blocking) ---
def compute_next_search_position(current_z, direction, lower=0, upper=20, step=1):
    # Oscillate Z between lower and upper bounds
    if direction > 0:
        next_z = current_z + step
        if next_z > upper:
            next_z = upper
            direction = -1
    else:
        next_z = current_z - step
        if next_z < lower:
            next_z = lower
            direction = 1
    return next_z, direction

def compute_mirror_angles(feet_point):
    # Placeholder for angle calculation
    # In production: convert feet_point to mirror angles with calibration
    return (0.0, 0.0)
