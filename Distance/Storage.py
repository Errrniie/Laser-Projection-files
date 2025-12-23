import json

CALIBRATION_FILE = "camera_calibration.json"

def save_calibration_data(data):
    """Saves the calibration data to a file."""
    try:
        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Calibration data saved to {CALIBRATION_FILE}")
    except IOError as e:
        print(f"Error saving calibration data: {e}")

def load_calibration_data():
    """Loads calibration data from a file."""
    try:
        with open(CALIBRATION_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Calibration file not found. Please run the calibration process.")
        return None
    except IOError as e:
        print(f"Error loading calibration data: {e}")
        return None
