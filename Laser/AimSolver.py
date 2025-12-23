# Laser/AimSolver.py
from Laser.GroundAim import vertical_angle_to_ground
from Laser.Calibration import (
    Y_NEUTRAL,
    Y_MM_PER_RAD,
    LASER_HEIGHT_M
)

def solve_ground_hit(distance_m):
    """
    Returns (x_mm, y_mm) motor targets to hit ground at distance.
    """
    theta_y = vertical_angle_to_ground(distance_m, LASER_HEIGHT_M)

    dy = -theta_y * Y_MM_PER_RAD
    y_target = Y_NEUTRAL + dy

    return y_target
