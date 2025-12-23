
import sys
import os
import cv2
import math
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Imports from our project
from YoloModel.YoloInterface import YoloInterface
from Distance.Model import load_model, get_distance
from Laser.LaserController import aim_at_coordinates
from Laser.LaserEnable import Controller as LaserEnableController
from Motion.Moonraker_ws import KlipperWs

# --- Configuration ---
CAMERA_INDEX = 4
CAMERA_WIDTH = 1080  # Make sure this matches your camera's resolution
CAMERA_HEIGHT = 720
# IMPORTANT: Calibrate this value for your specific camera for accurate aiming.
# It represents the horizontal field of view in degrees.
H_FOV_DEGREES = 55

# Convert FOV to radians for math
H_FOV_RADIANS = math.radians(H_FOV_DEGREES)

def pixel_to_meters(x_pixel, z_m):
    """
    Converts a pixel's x-coordinate to a real-world x-coordinate in meters
    based on the camera's horizontal field of view.
    """
    # Calculate the pixel's offset from the center of the image
    x_pixel_offset = x_pixel - (CAMERA_WIDTH / 2)

    # Calculate the angle of the pixel relative to the camera's center axis
    # This is a linear approximation, which is accurate for most cameras.
    angle_to_pixel = (x_pixel_offset / CAMERA_WIDTH) * H_FOV_RADIANS

    # Use trigonometry (tangent) to find the real-world x-coordinate
    x_m = z_m * math.tan(angle_to_pixel)
    return x_m

def main():
    """
    Main function to run the laser targeting test.
    """
    # --- Initialization ---
    print("Initializing systems...")
    yolo = YoloInterface()
    distance_model = load_model()
    laser_gpio = LaserEnableController()
    
    print("Connecting to Klipper...")
    ws_client = KlipperWs()
    
    # --- Main Loop ---
    try:
        print("Starting main loop. Press 'q' in the video window to exit.")
        while True:
            frame, detections = yolo.get_frame_and_detections()

            if frame is None:
                print("Could not get frame from camera, retrying...")
                time.sleep(0.1)
                continue

            target_person = None
            if detections:
                person_detections = [d for d in detections if d['label'] == 'person']
                if person_detections:
                    # Target the person with the largest bounding box (closest)
                    target_person = max(person_detections, key=lambda p: p['box'][2] * p['box'][3])

            if target_person:
                # --- Target Acquired ---
                box = target_person['box']
                x1, y1, w, h = map(int, box)
                x2, y2 = x1 + w, y1 + h

                # Define the target point: the center of the bottom edge of the box
                bottom_center_x = x1 + (w / 2)
                bottom_center_y = y2

                # Estimate distance (z-axis) using the calibrated model
                z_m = get_distance(distance_model, bottom_center_y)

                # Estimate horizontal position (x-axis) using the FOV calculation
                x_m = pixel_to_meters(bottom_center_x, z_m)

                print(f"TARGET DETECTED at pixel ({bottom_center_x:.1f}, {bottom_center_y:.1f})")
                print(f"  -> Estimated Coords: (x={x_m:.2f}m, z={z_m:.2f}m)")

                # Aim the laser and fire
                aim_at_coordinates(ws_client, x_m, z_m)
                laser_gpio.enable()

                # --- Visualization ---
                # Draw the bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Draw a red dot at the target point
                cv2.circle(frame, (int(bottom_center_x), int(bottom_center_y)), 7, (0, 0, 255), -1)

            else:
                # --- No Target ---
                # If no one is detected, turn the laser off
                laser_gpio.disable()

            # Display the video feed
            display_frame = cv2.resize(frame, (1280, 720)) # Resize for easier viewing
            cv2.imshow('Laser Test', display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\nCtrl+C detected. Exiting...")
    finally:
        # --- Cleanup ---
        print("Shutting down all systems...")
        yolo.stop()
        laser_gpio.disable()
        laser_gpio.cleanup()
        ws_client.close()
        cv2.destroyAllWindows()
        print("Cleanup complete. Exited gracefully.")

if __name__ == "__main__":
    main()
