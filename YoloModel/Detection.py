from ultralytics import YOLO

CONF_THRESH = 0.4
MODEL_PATH = "yolov8n.pt"
DEVICE = "cuda"

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
        device=0,
        conf=CONF_THRESH,
        verbose=False
    )

    boxes = results[0].boxes
    if boxes is None:
        return False, None, None, 0.0

    best_conf = 0.0
    best_box = None

    for box, cls, conf in zip(
        boxes.xyxy.cpu().numpy(),
        boxes.cls.cpu().numpy(),
        boxes.conf.cpu().numpy()
    ):
        if int(cls) != 0 or conf < CONF_THRESH:
            continue

        if conf > best_conf:
            best_conf = conf
            best_box = box.astype(int)

    if best_box is None:
        return False, None, None, 0.0

    x1, y1, x2, y2 = best_box
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2

    return True, (cx, cy), (x1, y1, x2, y2), best_conf
