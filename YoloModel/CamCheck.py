import cv2
import torch
from ultralytics import YOLO

# Load YOLOv8 model (PyTorch)
model = YOLO("yolov8n.pt")

# Force CUDA
model.to("cuda")

# Camera index: try 0, 1, 2
cap = cv2.VideoCapture(4, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

if not cap.isOpened():
    raise RuntimeError("Could not open camera")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # YOLO inference on GPU
    results = model(
        frame,
        device=0,      # CUDA device
        verbose=False
    )
    print(frame.shape)

    # Draw detections
    annotated = results[0].plot(img=frame)


    cv2.imshow("YOLO CUDA Webcam", annotated)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
