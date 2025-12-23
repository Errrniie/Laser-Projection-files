# Laser/LaserController.py
from Motion.Move import safe_move_and_wait
from Laser.Calibration import Y_NEUTRAL_MM, X_NEUTRAL_MM
from Laser.GroundAim import y_mm_for_ground_hit

def aim_ground_point(ws_client, distance_m: float, speed: int = 600):
    """
    Aim the laser to hit the ground at the measured distance, keeping X at neutral.
    """
    y_target = Y_NEUTRAL_MM + y_mm_for_ground_hit(distance_m)

    # For now: keep X neutral; you can add X later.
    # Your current motion code moves only one axis (Z). :contentReference[oaicite:1]{index=1}
    safe_move_and_wait(ws_client, z=y_target, speed=speed)
