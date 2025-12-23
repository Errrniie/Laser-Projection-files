import cv2
import sys
import os

# Adjust the Python path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Distance.Storage import save_calibration_data

calibration = []

# 10, 15, 20, ..., 65 ft
KNOWN_DISTANCES = list(range(15, 70, 5))

cap = cv2.VideoCapture(4)

last_click = None
frame_w = None
frame_h = None

def mouse_cb(event, x, y, flags, param):
    global last_click
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(calibration) < len(KNOWN_DISTANCES):
            d = KNOWN_DISTANCES[len(calibration)]
            calibration.append((y, d))
            last_click = (x, y)
            print(f"Captured y={y} at distance={d} ft")

cv2.namedWindow("calibrate")
cv2.setMouseCallback("calibrate", mouse_cb)

while cap.isOpened() and len(calibration) < len(KNOWN_DISTANCES):
    ret, frame = cap.read()
    if not ret:
        break

    if frame_w is None:
        frame_h, frame_w = frame.shape[:2]

    # draw vertical center line (light gray)
    cx = frame_w // 2
    cv2.line(frame, (cx, 0), (cx, frame_h), (200, 200, 200), 1)

    # draw last clicked point
    if last_click is not None:
        cv2.circle(frame, last_click, 5, (0, 0, 255), -1)

    # instruction text
    idx = len(calibration)
    if idx < len(KNOWN_DISTANCES):
        label = f"Click ground point at {KNOWN_DISTANCES[idx]} ft"
    else:
        label = "Calibration complete"

    cv2.putText(
        frame,
        label,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 255, 0),
        2,
        cv2.LINE_AA
    )

    cv2.imshow("calibrate", frame)

    if cv2.waitKey(1) == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()

print("Final calibration data:", calibration)

if calibration:
    print("Saving calibration data...")
    save_calibration_data(calibration)
else:
    print("No calibration data was captured.")
