import numpy as np
from numpy.polynomial.polynomial import Polynomial

# --- Globals ---
_model = None
_inverse_model = None

def load_model(calibration_data):
    """
    Loads the distance model from calibration data.
    The model is a polynomial fit to the (y, distance) data.
    """
    global _model, _inverse_model
    
    if not calibration_data:
        raise ValueError("Calibration data cannot be empty.")

    # Sort by distance to ensure correct interpolation
    calibration_data.sort(key=lambda p: p[1])

    y_coords = np.array([p[0] for p in calibration_data])
    distances = np.array([p[1] for p in calibration_data])

    # --- Create a polynomial model (y) -> distance ---
    # Fit a 2nd degree polynomial: distance = ay^2 + by + c
    _model = Polynomial.fit(y_coords, distances, 2)

    # --- Create an inverse model distance -> (y) ---
    _inverse_model = Polynomial.fit(distances, y_coords, 2)

    print("Distance model loaded.")

def get_distance(y):
    """
    Get the estimated distance for a given y-coordinate.
    """
    if _model is None:
        raise RuntimeError("Distance model not loaded. Call load_model() first.")
    
    # Clip the y-coordinate to the calibrated range to avoid extrapolation errors
    min_y, max_y = _model.domain
    clipped_y = np.clip(y, min_y, max_y)

    return _model(clipped_y)

def get_y(distance):
    """
    Get the estimated y-coordinate for a given distance.
    """
    if _inverse_model is None:
        raise RuntimeError("Distance model not loaded. Call load_model() first.")
    
    min_dist, max_dist = _inverse_model.domain
    clipped_dist = np.clip(distance, min_dist, max_dist)
    
    return _inverse_model(clipped_dist)
