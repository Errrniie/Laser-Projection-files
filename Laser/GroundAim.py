# Laser/GroundAim.py
import math
from Laser.Calibration import LASER_HEIGHT_M, Y_ROTATION_DISTANCE, Y_SIGN, mm_per_rad

def y_mm_for_ground_hit(distance_m: float) -> float:
    """
    Returns delta in Klipper units ("mm") for the mirror pitch axis
    needed to hit the ground at horizontal distance distance_m.
    """
    if distance_m <= 0:
        raise ValueError("distance_m must be > 0")

    theta_beam = math.atan(LASER_HEIGHT_M / distance_m)  # rad
    alpha_motor = 0.5 * theta_beam                       # mirror/motor rad (half-angle)
    dy_mm = Y_SIGN * alpha_motor * mm_per_rad(Y_ROTATION_DISTANCE)
    return dy_mm
