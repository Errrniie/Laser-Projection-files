
import time
import sys
import os
import cv2
import csv

# Adjust the Python path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Distance.YoloInterface import start_vision, stop_vision, detect_human_live
from Distance.Model import load_model, get_distance
from Distance.Storage import load_calibration_data, save_calibration_data

# --- Constants ---
# Generate distances from 15 to 70 feet, inclusive, in 5-foot increments
KNOWN_DISTANCES = list(range(15, 75, 5))

def run_calibration():
    """Runs the camera calibration process using mouse clicks."""
    print("Starting calibration process...")
    print("Click on the ground at the specified distances.")
    print("Press 'ESC' to quit.")

    calibration = []
    
    # Attempt to open the camera
    cap = cv2.VideoCapture(3)
    if not cap.isOpened():
        print("Could not open camera at index 4, trying index 0.")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open any video stream.")
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

        # Draw center line and last click
        cv2.line(frame, (frame_w // 2, 0), (frame_w // 2, frame_h), (200, 200, 200), 1)
        if last_click: cv2.circle(frame, last_click, 5, (0, 0, 255), -1)

        # Display instructions
        idx = len(calibration)
        label = f"Click ground point at {KNOWN_DISTANCES[idx]} ft" if idx < len(KNOWN_DISTANCES) else "Calibration complete!"
        cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)

        cv2.imshow("Calibrate Distance", frame)
        if cv2.waitKey(1) & 0xFF in [27, ord('q')]: # ESC or 'q'
            break

    cap.release()
    cv2.destroyAllWindows()

    if calibration:
        print("\nSaving calibration data...")
        save_calibration_data(calibration)

def save_comparison_data(data):
    """Saves the real vs. estimated distance data to a CSV file."""
    if not data:
        print("No comparison data to save.")
        return
    
    filename = "distance_comparison.csv"
    print(f"Saving comparison data to {filename}...")
    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["RealDistance", "EstimatedDistance", "PercentageError"])
            for row in data:
                real_dist, est_dist = row
                if real_dist != 0:
                    error = ((est_dist - real_dist) / real_dist) * 100
                else:
                    error = float('inf') # Avoid division by zero
                writer.writerow([real_dist, f"{est_dist:.2f}", f"{error:.2f}%"])
        print("Save complete.")
    except IOError as e:
        print(f"Error saving comparison data: {e}")

def test_model():
    """Tests the loaded distance model with live YOLO detection and logs comparisons."""
    print("\nStarting distance estimation test...")
    start_vision()
    
    comparison_data = []
    dist_idx = 0
    
    cv2.namedWindow("Distance Test")

    try:
        while dist_idx < len(KNOWN_DISTANCES):
            real_distance = KNOWN_DISTANCES[dist_idx]
            print(f"\nPosition the person at {real_distance} ft.")
            print("Press 'e' to record the estimated distance.")
            print("Press 'n' to move to the next distance.")
            print("Press 'q' to quit.")
            
            while True:
                human, _, bbox, _, frame, feet_center = detect_human_live()

                if frame is not None:
                    vis = frame.copy()
                    
                    # Draw bounding box
                    if bbox:
                        x1, y1, x2, y2 = bbox
                        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Draw feet center and display distance
                    if human and feet_center:
                        estimated_distance = get_distance(feet_center[1])
                        dist_text = f"Est. Distance: {estimated_distance:.2f} ft"
                        cv2.drawMarker(vis, feet_center, (0, 0, 255), cv2.MARKER_STAR, 20, 2)
                        cv2.putText(vis, dist_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    
                    # Display current real distance
                    real_dist_text = f"Real Distance: {real_distance} ft"
                    cv2.putText(vis, real_dist_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    
                    cv2.imshow("Distance Test", vis)

                key = cv2.waitKey(1) & 0xFF

                if key == ord('e'):
                    if human and feet_center:
                        estimated_distance = get_distance(feet_center[1])
                        comparison_data.append([real_distance, estimated_distance])
                        error = ((estimated_distance - real_distance) / real_distance) * 100
                        print(f"  Recorded: Real={real_distance} ft, Est={estimated_distance:.2f} ft, Error={error:.2f}%")
                    else:
                        print("  Cannot record: No person detected.")
                
                elif key == ord('n'):
                    dist_idx += 1
                    break # Breaks inner loop to move to the next distance
                
                elif key in [ord('q'), 27]: # q or ESC
                    dist_idx = len(KNOWN_DISTANCES) # End the outer loop
                    break

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        print("\nStopping vision system...")
        stop_vision()
        cv2.destroyAllWindows()
        save_comparison_data(comparison_data)

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
            choice = input("Calibration data found. Run new calibration (c) or start test (t)? ").lower()
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
