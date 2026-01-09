from ultralytics import YOLO
from typing import List, Tuple, Optional

CONF_THRESH = 0.6
MODEL_PATH = "yolov8s.pt"
DEVICE = "cpu"

# Image size for YOLO inference
# Higher values = better detection of small/distant objects, but slower
# Common values: 640 (default/fast), 960, 1280 (best for distant objects)
# For 1080p video, use 1280 to avoid shrinking the frame too much
IMGSZ = 1280

# Tiled inference settings
USE_TILED_INFERENCE = True  # Set to False to disable tiling
NMS_IOU_THRESHOLD = 0.5     # IoU threshold for merging detections

model = YOLO(MODEL_PATH)
model.to(DEVICE)


def _run_yolo_inference(frame, imgsz=None):
    """
    Internal function to run YOLO inference on a single image.
    
    Args:
        frame: Input image/frame
        imgsz: Image size for inference
    
    Returns:
        List of (bbox, confidence) tuples where bbox is (x1, y1, x2, y2)
    """
    img_size = imgsz if imgsz is not None else IMGSZ
    
    results = model(
        frame,
        device=DEVICE,
        conf=CONF_THRESH,
        classes=[0],
        imgsz=img_size,
        verbose=False
    )
    
    detections = []
    
    if not results or not results[0].boxes:
        return detections
    
    boxes = results[0].boxes
    if not hasattr(boxes, 'conf') or not hasattr(boxes, 'xyxy'):
        return detections
    
    for i in range(len(boxes.conf)):
        conf = boxes.conf[i].item()
        bbox = boxes.xyxy[i].cpu().numpy().astype(int)
        detections.append((tuple(bbox), conf))
    
    return detections


def detect_human_single(frame, imgsz=None):
    """
    Runs YOLO once on the full frame (original non-tiled approach).
    
    Args:
        frame: Input image/frame
        imgsz: Optional image size override. If None, uses global IMGSZ.
    
    Returns:
        human_present (bool)
        bbox_center (cx, cy) or None
        bbox (x1, y1, x2, y2) or None
        confidence (float)
    """
    detections = _run_yolo_inference(frame, imgsz)
    
    if not detections:
        return False, None, None, 0.0
    
    # Find best detection
    best_conf = 0.0
    best_box = None
    
    for bbox, conf in detections:
        if conf > best_conf:
            best_conf = conf
            best_box = bbox
    
    if best_box is None:
        return False, None, None, 0.0
    
    x1, y1, x2, y2 = best_box
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    
    return True, (cx, cy), (x1, y1, x2, y2), best_conf


def detect_human_tiled(frame, imgsz=None, tile_config=None):
    """
    Runs YOLO using tiled inference for better small object detection.
    
    The frame is split into overlapping tiles, YOLO is run on each tile,
    and results are merged using Non-Maximum Suppression.
    
    Args:
        frame: Input image/frame (should be high resolution for best results)
        imgsz: Optional image size override for YOLO inference
        tile_config: Optional TileConfig override
    
    Returns:
        human_present (bool)
        bbox_center (cx, cy) or None
        bbox (x1, y1, x2, y2) or None  
        confidence (float)
    """
    from YoloModel.Tiling import (
        extract_tiles, merge_tile_detections, get_best_detection,
        Detection, get_tile_config
    )
    
    config = tile_config if tile_config is not None else get_tile_config()
    
    # Extract tiles from frame
    tiles = extract_tiles(frame, config)
    
    # Run inference on each tile
    all_detections = []
    for tile in tiles:
        raw_dets = _run_yolo_inference(tile.image, imgsz)
        
        # Convert to Detection objects
        tile_dets = [
            Detection(
                x1=bbox[0], y1=bbox[1], x2=bbox[2], y2=bbox[3],
                confidence=conf, class_id=0
            )
            for bbox, conf in raw_dets
        ]
        all_detections.append(tile_dets)
    
    # Merge detections from all tiles
    merged = merge_tile_detections(all_detections, tiles, NMS_IOU_THRESHOLD)
    
    # Get best detection
    best = get_best_detection(merged)
    
    if best is None:
        return False, None, None, 0.0
    
    bbox = best.to_tuple()
    center = best.center
    
    return True, center, bbox, best.confidence


def detect_human(frame, imgsz=None, use_tiling=None):
    """
    Runs YOLO detection on frame.
    
    By default, uses tiled inference for better detection of small/distant
    objects. Can be disabled globally or per-call.
    
    Args:
        frame: Input image/frame
        imgsz: Optional image size override. If None, uses global IMGSZ.
        use_tiling: Override tiling behavior. If None, uses global setting.
                    Set to False to force single-frame inference.
    
    Returns:
        human_present (bool)
        bbox_center (cx, cy) or None
        bbox (x1, y1, x2, y2) or None
        confidence (float)
    """
    tiling_enabled = use_tiling if use_tiling is not None else USE_TILED_INFERENCE
    
    if tiling_enabled:
        return detect_human_tiled(frame, imgsz)
    else:
        return detect_human_single(frame, imgsz)


def detect_human_all(frame, imgsz=None, use_tiling=None):
    """
    Detect all humans in frame (not just the best one).
    
    Args:
        frame: Input image/frame
        imgsz: Optional image size override
        use_tiling: Override tiling behavior
    
    Returns:
        List of tuples: [(bbox, center, confidence), ...]
        where bbox is (x1, y1, x2, y2) and center is (cx, cy)
    """
    tiling_enabled = use_tiling if use_tiling is not None else USE_TILED_INFERENCE
    
    if tiling_enabled:
        from YoloModel.Tiling import (
            extract_tiles, merge_tile_detections, Detection, get_tile_config
        )
        
        config = get_tile_config()
        tiles = extract_tiles(frame, config)
        
        all_detections = []
        for tile in tiles:
            raw_dets = _run_yolo_inference(tile.image, imgsz)
            tile_dets = [
                Detection(
                    x1=bbox[0], y1=bbox[1], x2=bbox[2], y2=bbox[3],
                    confidence=conf, class_id=0
                )
                for bbox, conf in raw_dets
            ]
            all_detections.append(tile_dets)
        
        merged = merge_tile_detections(all_detections, tiles, NMS_IOU_THRESHOLD)
        
        results = []
        for det in merged:
            bbox = det.to_tuple()
            center = det.center
            results.append((bbox, center, det.confidence))
        return results
    else:
        detections = _run_yolo_inference(frame, imgsz)
        results = []
        for bbox, conf in detections:
            x1, y1, x2, y2 = bbox
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            results.append((bbox, (cx, cy), conf))
        return results


def set_imgsz(size):
    """
    Set the global YOLO inference image size.
    
    Args:
        size: Image size (int). Common values:
              - 640: Fast, good for close objects (default YOLO)
              - 960: Balanced
              - 1280: Best for distant/small objects, slower
              - 1920: Maximum quality for 1080p video, slowest
    """
    global IMGSZ
    IMGSZ = size
    print(f"YOLO image size set to: {IMGSZ}")


def get_imgsz():
    """Get the current YOLO inference image size."""
    return IMGSZ


def set_confidence(thresh):
    """
    Set the confidence threshold for detection.
    
    Args:
        thresh: Confidence threshold (0.0 to 1.0)
                Lower = more detections but more false positives
                Higher = fewer detections but more reliable
    """
    global CONF_THRESH
    CONF_THRESH = thresh
    print(f"YOLO confidence threshold set to: {CONF_THRESH}")


def set_tiled_inference(enabled: bool):
    """
    Enable or disable tiled inference globally.
    
    Args:
        enabled: True to use tiled inference, False for single-frame
    """
    global USE_TILED_INFERENCE
    USE_TILED_INFERENCE = enabled
    print(f"Tiled inference: {'ENABLED' if enabled else 'DISABLED'}")


def is_tiled_inference_enabled() -> bool:
    """Check if tiled inference is currently enabled."""
    return USE_TILED_INFERENCE


def set_nms_threshold(threshold: float):
    """
    Set the NMS IoU threshold for merging tile detections.
    
    Args:
        threshold: IoU threshold (0.0 to 1.0)
                   Lower = more aggressive merging (fewer duplicates)
                   Higher = less aggressive merging
    """
    global NMS_IOU_THRESHOLD
    NMS_IOU_THRESHOLD = threshold
    print(f"NMS IoU threshold set to: {NMS_IOU_THRESHOLD}")


def configure_tiling(rows: int = 2, cols: int = 2, overlap: float = 0.15):
    """
    Configure the tile grid for tiled inference.
    
    Args:
        rows: Number of tile rows (default 2)
        cols: Number of tile columns (default 2)  
        overlap: Overlap percentage between tiles (default 0.15 = 15%)
    
    Example:
        configure_tiling(2, 2, 0.15)  # 2x2 grid with 15% overlap (4 tiles)
        configure_tiling(3, 3, 0.20)  # 3x3 grid with 20% overlap (9 tiles)
    """
    from YoloModel.Tiling import set_tile_config
    set_tile_config(rows, cols, overlap)


def get_tiling_info() -> dict:
    """
    Get current tiling configuration info.
    
    Returns:
        Dictionary with tiling settings
    """
    from YoloModel.Tiling import get_tile_config
    config = get_tile_config()
    return {
        "enabled": USE_TILED_INFERENCE,
        "grid_rows": config.grid_rows,
        "grid_cols": config.grid_cols,
        "total_tiles": config.grid_rows * config.grid_cols,
        "overlap_percent": config.overlap_percent,
        "nms_threshold": NMS_IOU_THRESHOLD,
        "imgsz": IMGSZ
    }
