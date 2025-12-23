# Laser/GroundAim.py
import math
from Laser.Calibration import (
    LASER_HEIGHT_M, 
    Y_ROTATION_DISTANCE, 
    X_ROTATION_DISTANCE, 
    Y_SIGN, 
    X_SIGN, 
    mm_per_rad
)

def get_motor_deltas_for_ground_hit(x_m: float, z_m: float) -> tuple[float, float]:
    """
    Returns delta in Klipper units ("mm") for the mirror pitch and yaw axes
    needed to hit the ground at horizontal coordinates (x_m, z_m).
    """
    if z_m <= 0:
        raise ValueError("z_m must be > 0")

    # Y-axis (pitch) calculation
    ground_dist = math.sqrt(x_m**2 + z_m**2)
    theta_beam_y = math.atan(LASER_HEIGHT_M / ground_dist)  # rad
    alpha_motor_y = 0.5 * theta_beam_y                       # mirror/motor rad (half-angle)
    dy_mm = Y_SIGN * alpha_motor_y * mm_per_rad(Y_ROTATION_DISTANCE)

    # X-axis (yaw) calculation
    theta_beam_x = math.atan2(x_m, z_m) # rad
    alpha_motor_x = 0.5 * theta_beam_x  # mirror/motor rad (half-angle)
    dx_mm = X_SIGN * alpha_motor_x * mm_per_rad(X_ROTATION_DISTANCE)

    return dx_mm, dy_mm
