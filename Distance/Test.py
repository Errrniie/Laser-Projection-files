import time
import sys
import os

# Adjust the Python path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Distance.YoloInterface import start_vision, stop_vision, detect_human_live, show_frame
from Distance.Model import load_model, get_distance
from Distance.Storage import load_calibration_data

def test_model():
    """Tests the loaded distance model."""
    print("\nStarting distance estimation test...")
    start_vision()

    try:
        while True:
            human, _, _, _, frame, feet_center = detect_human_live()

            if frame is not None:
                show_frame(frame, feet_center=feet_center)

            if human and feet_center:
                estimated_distance = get_distance(feet_center[1])
                print(f"Feet Y: {feet_center[1]} -> Estimated Distance: {estimated_distance:.2f} ft")
            
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("Test interrupted by user.")
    finally:
        stop_vision()

if __name__ == "__main__":
    # Load existing calibration data
    calibration_data = load_calibration_data()

    if calibration_data:
        load_model(calibration_data)
        test_model()
    else:
        print("No calibration data found. Please run Distance/Calibration.py first.")
