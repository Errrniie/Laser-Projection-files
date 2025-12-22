# YoloModel/YoloInterface.py

from YoloModel.Detection import detect_human
from YoloModel.CameraThread import CameraThread
import cv2

camera = CameraThread(index=4, width=640, height=480, fps=30)
camera.start()

_WINDOW_NAME = "Goose Vision"
DRAW_EVERY = 1
_frame_count = 0


def detect_human_live():
    frame = camera.get_frame()
    if frame is None:
        return False, None, None, 0.0, None

    human, center, bbox, conf = detect_human(frame)
    return human, center, bbox, conf, frame


def show_frame(frame, bbox=None, conf=None):
    global _frame_count
    _frame_count += 1
    if _frame_count % DRAW_EVERY != 0:
        return

    vis = frame.copy()

    if bbox is not None:
        x1, y1, x2, y2 = bbox
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            vis,
            f"{conf:.2f}",
            (x1, y1 - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )

    h, w = vis.shape[:2]
    cv2.drawMarker(
        vis,
        (w // 2, h // 2),
        (255, 0, 0),
        cv2.MARKER_CROSS,
        20,
        2,
    )

    cv2.imshow(_WINDOW_NAME, vis)
    cv2.waitKey(1)
