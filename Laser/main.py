
import sys
import os
import cv2
import math
import time
import traceback

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Imports from our project
from Distance import YoloInterface # CORRECTED: Import the CLASS
from Distance.Storage import load_calibration_data
from Laser.LaserController import aim_at_coordinates
from Laser.LaserEnable import Controller as LaserEnableController
from Motion.Moonraker_ws import MoonrakerWSClient
from Distance.DistanceFromJSON import distance_from_y

# --- Configuration ---
CAMERA_WIDTH = 640 
CAMERA_HEIGHT = 480
H_FOV_DEGREES = 55.0
KLIPPER_WS_URL = "ws://192.168.8.146:7125/websocket"
WINDOW_NAME = "Laser Target System"


AIM_INTERVAL = 0.15

# Convert FOV to radians for math
H_FOV_RADIANS = math.radians(H_FOV_DEGREES)

def pixel_to_meters(x_pixel, z_m):
    x_pixel_offset = x_pixel - (CAMERA_WIDTH / 2)
    angle_to_pixel = (x_pixel_offset / CAMERA_WIDTH) * H_FOV_RADIANS
    x_m = z_m * math.tan(angle_to_pixel)
    return x_m

def main():
    last_aim_time = 0.0
    ws_client = None
    laser_gpio = None
    vision_controller = None

    try:
        # --- Initialization ---
        print("Initializing systems...")
        
        # CORRECTED: Instantiate the YoloInterface class
        YoloInterface.start_vision()
        
        print("Loading calibration data...")
        calibration_data = load_calibration_data()
        if not calibration_data:
            print("ERROR: Calibration data not found. Please run calibration first.")
            return

        laser_gpio = LaserEnableController()
        
        print(f"Connecting to Klipper at {KLIPPER_WS_URL}...")
        ws_client = MoonrakerWSClient(KLIPPER_WS_URL)
        ws_client.connect()


        time.sleep(2.0) # Wait for camera to be ready
        
        # --- Main Loop ---
        print("Starting main loop. Press 'q' in the video window to exit.")
        while True:
            # CORRECTED: Call the get_frame_and_detections() method
            is_human, center, bbox, conf, frame, feet_center = YoloInterface.detect_human_live()


            if frame is None:
                time.sleep(0.01)
                continue

            if is_human and feet_center:
                bottom_center_x, bottom_center_y = feet_center

                z_ft = distance_from_y(bottom_center_y, calibration_data)
                z_m = z_ft * 0.3048

                x_m = pixel_to_meters(bottom_center_x, z_m)

                print(f"TARGET DETECTED at pixel ({bottom_center_x:.1f}, {bottom_center_y:.1f})")
                print(f"  -> Estimated Coords: (x={x_m:.2f}m, z={z_m:.2f}m)")

                now = time.time()
                if now - last_aim_time > AIM_INTERVAL:
                    aim_at_coordinates(ws_client, x_m, z_m, speed=800)
                    last_aim_time = now

                laser_gpio.set_laser(True)

 

                # --- Visualization ---
                if bbox:
                    x1, y1, x2, y2 = bbox
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.circle(frame, (int(bottom_center_x), int(bottom_center_y)), 7, (0, 0, 255), -1)

            else:
                if laser_gpio:
                    laser_gpio.set_laser(False)

            cv2.imshow(WINDOW_NAME, frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except (KeyboardInterrupt, Exception) as e:
        if isinstance(e, KeyboardInterrupt):
            print("\nCtrl+C detected. Exiting...")
        else:
            print(f"An unexpected error occurred: {e}")
            traceback.print_exc()

    finally:
        # --- Cleanup ---
        print("Shutting down all systems...")
        if laser_gpio:
            laser_gpio.set_laser(False)
        
        # No stop_vision() needed, handled by class destructor
        if ws_client:
            ws_client.close()
        
        cv2.destroyAllWindows()
        print("Cleanup complete. Exited gracefully.")

if __name__ == "__main__":
    main()
