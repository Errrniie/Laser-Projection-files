import math

# Laser/Calibration.py
Y_SIGN = +1   # if +Z moves beam DOWN; else -1
X_SIGN = +1

# Neutral motor positions (mm)
X_NEUTRAL_MM = 5.75
Y_NEUTRAL_MM = 3.8

Y_MIN = 0
Y_MAX = 7.6

X_MIN = 0
X_MAX = 11.5

# Klipper scaling: rotation_distance for each mirror axis stepper
# (These are FROM your printer.cfg for those steppers)
Y_ROTATION_DISTANCE = 40.0  # <-- replace with your actual value
X_ROTATION_DISTANCE = 40.0  # <-- replace with your actual value

# Physical setup
LASER_HEIGHT_M = 1.4097  # <-- measure this

def mm_per_rad(rotation_distance: float) -> float:
    return rotation_distance / (2 * math.pi)
    
