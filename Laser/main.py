
import sys
import os
import cv2
import math
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Imports from our project
from Distance import YoloInterface as Vision
from Distance.Model import load_model, get_distance
from Laser.LaserController import aim_at_coordinates
from Laser.LaserEnable import Controller as LaserEnableController
from Motion.Moonraker_ws import MoonrakerWSClient
from Distance.Storage import load_calibration_data

# --- Configuration ---
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
H_FOV_DEGREES = 55.0
KLIPPER_WS_URL = "ws://127.0.0.1:7125/websocket"
calibration_data = load_calibration_data()

# Convert FOV to radians for math
H_FOV_RADIANS = math.radians(H_FOV_DEGREES)

def pixel_to_meters(x_pixel, z_m):
    x_pixel_offset = x_pixel - (CAMERA_WIDTH / 2)
    angle_to_pixel = (x_pixel_offset / CAMERA_WIDTH) * H_FOV_RADIANS
    x_m = z_m * math.tan(angle_to_pixel)
    return x_m

def main():
    ws_client = None
    laser_gpio = None
    
    try:
        # --- Initialization ---
        print("Initializing systems...")
        Vision.start_vision()
        distance_model = load_model(calibration_data)
        laser_gpio = LaserEnableController()
        
        print(f"Connecting to Klipper at {KLIPPER_WS_URL}...")
        ws_client = MoonrakerWSClient(KLIPPER_WS_URL)

        time.sleep(2.0) # Wait for systems to be ready
        
        # --- Main Loop ---
        print("Starting main loop. Press 'q' in the video window to exit.")
        while True:
            is_human, center, bbox, conf, frame = Vision.detect_human_live()

            if frame is None:
                time.sleep(0.01)
                continue

            if is_human:
                x1, y1, x2, y2 = bbox
                bottom_center_x = (x1 + x2) / 2
                bottom_center_y = y2

                z_m = get_distance(distance_model, bottom_center_y)
                x_m = pixel_to_meters(bottom_center_x, z_m)

                print(f"TARGET DETECTED at pixel ({bottom_center_x:.1f}, {bottom_center_y:.1f})")
                print(f"  -> Estimated Coords: (x={x_m:.2f}m, z={z_m:.2f}m)")

                aim_at_coordinates(ws_client, x_m, z_m, speed=1000)
                laser_gpio.set_laser(True) # CORRECTED from enable()

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.circle(frame, (int(bottom_center_x), int(bottom_center_y)), 7, (0, 0, 255), -1)

            else:
                laser_gpio.set_laser(False) # CORRECTED from disable()

            Vision.show_frame(frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except (KeyboardInterrupt, Exception) as e:
        if isinstance(e, KeyboardInterrupt):
            print("\nCtrl+C detected. Exiting...")
        else:
            print(f"An unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()

    finally:
        # --- Cleanup ---
        print("Shutting down all systems...")
        if laser_gpio:
            laser_gpio.set_laser(False) # CORRECTED from disable()
        Vision.stop_vision()
        if ws_client:
            ws_client.close()
        print("Cleanup complete. Exited gracefully.")

if __name__ == "__main__":
    main()
