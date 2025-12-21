import cv2
from YoloModel.Detection import detect_human

CAMERA_INDEX = 4

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

def detect_human_live():
    ret, frame = cap.read()
    if not ret:
        return False, None, None, 0.0
    return detect_human(frame)
