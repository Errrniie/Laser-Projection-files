import time
import sys
import os
import cv2

# Adjust the Python path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Distance.YoloInterface import start_vision, stop_vision, detect_human_live, show_frame
from Distance.Model import load_model, get_distance
from Distance.Storage import load_calibration_data, save_calibration_data

def run_calibration():
    """Runs the camera calibration process using mouse clicks."""
    print("Starting calibration process...")
    print("Click on the ground at the specified distances.")
    print("Press 'ESC' to quit.")

    calibration = []
    KNOWN_DISTANCES = list(range(15, 70, 5)) # Distances in feet

    cap = cv2.VideoCapture(4)
    if not cap.isOpened():
        print("Error: Could not open video stream.")
        return

    last_click = None
    frame_w, frame_h = None, None

    def mouse_cb(event, x, y, flags, param):
        nonlocal last_click
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(calibration) < len(KNOWN_DISTANCES):
                d = KNOWN_DISTANCES[len(calibration)]
                calibration.append((y, d))
                last_click = (x, y)
                print(f"Captured y={y} at distance={d} ft")

    cv2.namedWindow("Calibrate Distance")
    cv2.setMouseCallback("Calibrate Distance", mouse_cb)

    while cap.isOpened() and len(calibration) < len(KNOWN_DISTANCES):
        ret, frame = cap.read()
        if not ret:
            break

        if frame_w is None:
            frame_h, frame_w = frame.shape[:2]

        # Draw center line
        cv2.line(frame, (frame_w // 2, 0), (frame_w // 2, frame_h), (200, 200, 200), 1)

        # Draw last clicked point
        if last_click:
            cv2.circle(frame, last_click, 5, (0, 0, 255), -1)

        # Display instructions
        idx = len(calibration)
        label = f"Click ground point at {KNOWN_DISTANCES[idx]} ft" if idx < len(KNOWN_DISTANCES) else "Calibration complete!"
        cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)

        cv2.imshow("Calibrate Distance", frame)
        if cv2.waitKey(1) == 27: # ESC key
            break

    cap.release()
    cv2.destroyAllWindows()

    if calibration:
        print("\nSaving calibration data...")
        save_calibration_data(calibration)
    else:
        print("\nNo calibration data was captured.")

def test_model():
    """Tests the loaded distance model with live YOLO detection."""
    print("\nStarting distance estimation test...")
    start_vision()

    try:
        while True:
            human, _, _, _, frame, feet_center = detect_human_live()

            if frame is not None:
                # Display the distance on the frame
                if human and feet_center:
                    estimated_distance = get_distance(feet_center[1])
                    dist_text = f"Estimated Distance: {estimated_distance:.2f} ft"
                    cv2.putText(frame, dist_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                show_frame(frame, feet_center=feet_center)

            if human and feet_center:
                estimated_distance = get_distance(feet_center[1])
                # Use carriage return to print on the same line
                sys.stdout.write(f"\rFeet Y: {feet_center[1]} -> Estimated Distance: {estimated_distance:.2f} ft        ")
                sys.stdout.flush()

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        print("\nStopping vision system...")
        stop_vision()

if __name__ == "__main__":
    calibration_data = load_calibration_data()

    def run_test_after_calibration():
        new_data = load_calibration_data()
        if new_data:
            print("\nCalibration complete. Loading model and starting test...")
            load_model(new_data)
            test_model()
        else:
            print("\nCould not load new calibration data. Exiting.")

    if not calibration_data:
        print("No calibration data found.")
        run_calibration()
        run_test_after_calibration()
    else:
        while True:
            choice = input("Calibration data found. Run new calibration (c) or test model (t)? ").lower()
            if choice == 'c':
                run_calibration()
                run_test_after_calibration()
                break
            elif choice == 't':
                load_model(calibration_data)
                test_model()
                break
            else:
                print("Invalid choice. Please enter 'c' or 't'.")
