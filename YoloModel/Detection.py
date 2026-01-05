from ultralytics import YOLO

CONF_THRESH = 0.6
MODEL_PATH = "yolov8n.pt"
DEVICE = "cpu"

model = YOLO(MODEL_PATH)
model.to(DEVICE)

def detect_human(frame):
    """
    Runs YOLO once.
    Returns:
        human_present (bool)
        bbox_center (cx, cy) or None
        bbox (x1, y1, x2, y2) or None
        confidence (float)
    """
    results = model(
        frame,
        device=DEVICE,
        conf=CONF_THRESH,
        classes=[0],
        verbose=False
    )

    if not results or not results[0].boxes:
        return False, None, None, 0.0

    boxes = results[0].boxes
    if not hasattr(boxes, 'conf') or not hasattr(boxes, 'xyxy'):
        return False, None, None, 0.0

    best_conf = 0.0
    best_box = None

    for i in range(len(boxes.conf)):
        conf = boxes.conf[i].item()
        if conf > best_conf:
            best_conf = conf
            best_box = boxes.xyxy[i].cpu().numpy().astype(int)

    if best_box is None:
        return False, None, None, 0.0

    x1, y1, x2, y2 = best_box
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2

    return True, (cx, cy), (x1, y1, x2, y2), best_conf
