# YoloModel/Tiling.py
"""
Tiled inference module for YOLO object detection.

This module provides utilities for splitting high-resolution frames into 
overlapping tiles, running inference on each tile, and merging the results
back into full-frame coordinates with Non-Maximum Suppression (NMS).

The tiled approach preserves native pixel density for each region, improving
detection of small/distant objects that would otherwise be lost when 
downscaling a 4K frame to YOLO's inference resolution.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
from Config.vision_config import get_tiling_config

# Load configuration
_tiling_config = get_tiling_config()

@dataclass
class TileConfig:
    """Configuration for tile-based inference."""
    grid_rows: int = _tiling_config.grid_rows          # Number of tile rows
    grid_cols: int = _tiling_config.grid_cols          # Number of tile columns
    overlap_percent: float = _tiling_config.overlap_percent  # Overlap between tiles (0.0 to 0.5)
    
    def __post_init__(self):
        """Validate configuration."""
        if self.grid_rows < 1 or self.grid_cols < 1:
            raise ValueError("Grid dimensions must be at least 1x1")
        if not 0.0 <= self.overlap_percent <= 0.5:
            raise ValueError("Overlap percent must be between 0.0 and 0.5")


@dataclass
class Detection:
    """A single detection result."""
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    class_id: int = 0  # Default to person class
    
    @property
    def area(self) -> int:
        """Calculate bounding box area."""
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of bounding box."""
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)
    
    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Return bbox as (x1, y1, x2, y2) tuple."""
        return (self.x1, self.y1, self.x2, self.y2)


@dataclass 
class Tile:
    """Represents a single tile extracted from a frame."""
    image: np.ndarray       # The tile image data
    x_offset: int           # X offset in original frame
    y_offset: int           # Y offset in original frame
    width: int              # Tile width
    height: int             # Tile height
    row: int                # Tile row index
    col: int                # Tile column index


def calculate_tile_regions(
    frame_height: int,
    frame_width: int,
    config: TileConfig
) -> List[Tuple[int, int, int, int]]:
    """
    Calculate the regions (x1, y1, x2, y2) for each tile.
    
    Args:
        frame_height: Height of the full frame
        frame_width: Width of the full frame
        config: Tile configuration
    
    Returns:
        List of (x1, y1, x2, y2) tuples for each tile region
    """
    regions = []
    
    # Calculate base tile size (without overlap)
    base_tile_h = frame_height / config.grid_rows
    base_tile_w = frame_width / config.grid_cols
    
    # Calculate overlap in pixels
    overlap_h = int(base_tile_h * config.overlap_percent)
    overlap_w = int(base_tile_w * config.overlap_percent)
    
    # Calculate actual tile size (with overlap added)
    tile_h = int(base_tile_h + overlap_h)
    tile_w = int(base_tile_w + overlap_w)
    
    for row in range(config.grid_rows):
        for col in range(config.grid_cols):
            # Calculate tile position
            y1 = int(row * base_tile_h) - (overlap_h // 2 if row > 0 else 0)
            x1 = int(col * base_tile_w) - (overlap_w // 2 if col > 0 else 0)
            
            # Clamp to frame bounds
            y1 = max(0, y1)
            x1 = max(0, x1)
            
            y2 = min(frame_height, y1 + tile_h)
            x2 = min(frame_width, x1 + tile_w)
            
            # Adjust if we hit the edge
            if y2 == frame_height and y2 - y1 < tile_h:
                y1 = max(0, frame_height - tile_h)
            if x2 == frame_width and x2 - x1 < tile_w:
                x1 = max(0, frame_width - tile_w)
            
            regions.append((x1, y1, x2, y2))
    
    return regions


def extract_tiles(frame: np.ndarray, config: TileConfig) -> List[Tile]:
    """
    Extract overlapping tiles from a frame.
    
    Args:
        frame: Input frame (H, W, C) numpy array
        config: Tile configuration
    
    Returns:
        List of Tile objects
    """
    h, w = frame.shape[:2]
    regions = calculate_tile_regions(h, w, config)
    
    tiles = []
    for idx, (x1, y1, x2, y2) in enumerate(regions):
        row = idx // config.grid_cols
        col = idx % config.grid_cols
        
        tile_img = frame[y1:y2, x1:x2]
        
        tiles.append(Tile(
            image=tile_img,
            x_offset=x1,
            y_offset=y1,
            width=x2 - x1,
            height=y2 - y1,
            row=row,
            col=col
        ))
    
    return tiles


def convert_to_frame_coords(
    detections: List[Detection],
    tile: Tile
) -> List[Detection]:
    """
    Convert tile-relative detections to full-frame coordinates.
    
    Args:
        detections: List of detections with tile-relative coordinates
        tile: The tile these detections came from
    
    Returns:
        List of detections with full-frame coordinates
    """
    converted = []
    for det in detections:
        converted.append(Detection(
            x1=det.x1 + tile.x_offset,
            y1=det.y1 + tile.y_offset,
            x2=det.x2 + tile.x_offset,
            y2=det.y2 + tile.y_offset,
            confidence=det.confidence,
            class_id=det.class_id
        ))
    return converted


def calculate_iou(box1: Detection, box2: Detection) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    
    Args:
        box1: First detection
        box2: Second detection
    
    Returns:
        IoU value between 0.0 and 1.0
    """
    # Calculate intersection
    x1 = max(box1.x1, box2.x1)
    y1 = max(box1.y1, box2.y1)
    x2 = min(box1.x2, box2.x2)
    y2 = min(box1.y2, box2.y2)
    
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    
    if intersection == 0:
        return 0.0
    
    # Calculate union
    area1 = box1.area
    area2 = box2.area
    union = area1 + area2 - intersection
    
    if union == 0:
        return 0.0
    
    return intersection / union


def non_max_suppression(
    detections: List[Detection],
    iou_threshold: float = None
) -> List[Detection]:
    """
    Apply Non-Maximum Suppression to remove duplicate detections.
    
    Args:
        detections: List of all detections from all tiles
        iou_threshold: IoU threshold for considering boxes as duplicates (uses config default if None)
    
    Returns:
        Filtered list of detections with duplicates removed
    """
    if iou_threshold is None:
        iou_threshold = _tiling_config.merge_iou_threshold
    if not detections:
        return []
    
    # Sort by confidence (highest first)
    sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
    
    keep = []
    while sorted_dets:
        # Keep the highest confidence detection
        best = sorted_dets.pop(0)
        keep.append(best)
        
        # Remove detections that overlap too much with the best one
        remaining = []
        for det in sorted_dets:
            if calculate_iou(best, det) < iou_threshold:
                remaining.append(det)
        sorted_dets = remaining
    
    return keep


def merge_tile_detections(
    all_detections: List[List[Detection]],
    tiles: List[Tile],
    iou_threshold: float = None
) -> List[Detection]:
    """
    Merge detections from multiple tiles into a single list.
    
    This function:
    1. Converts all tile-relative coordinates to frame coordinates
    2. Applies NMS to remove duplicates from overlapping regions
    
    Args:
        all_detections: List of detection lists, one per tile
        tiles: Corresponding tile information for coordinate conversion
        iou_threshold: IoU threshold for NMS (uses config default if None)
    
    Returns:
        Merged and filtered detections in frame coordinates
    """
    if iou_threshold is None:
        iou_threshold = _tiling_config.merge_iou_threshold
    
    # Convert all detections to frame coordinates
    frame_detections = []
    for dets, tile in zip(all_detections, tiles):
        converted = convert_to_frame_coords(dets, tile)
        frame_detections.extend(converted)
    
    # Apply NMS to remove duplicates
    merged = non_max_suppression(frame_detections, iou_threshold)
    
    return merged


def get_best_detection(detections: List[Detection]) -> Optional[Detection]:
    """
    Get the detection with highest confidence.
    
    Args:
        detections: List of detections
    
    Returns:
        Detection with highest confidence, or None if list is empty
    """
    if not detections:
        return None
    return max(detections, key=lambda d: d.confidence)


# Default tile configuration
_default_tile_config = TileConfig(
    grid_rows=_tiling_config.grid_rows,
    grid_cols=_tiling_config.grid_cols,
    overlap_percent=_tiling_config.overlap_percent
)


def set_tile_config(rows: int = None, cols: int = None, overlap: float = None):
    """
    Update the default tile configuration.
    
    Args:
        rows: Number of tile rows (uses config default if None)
        cols: Number of tile columns (uses config default if None)  
        overlap: Overlap percentage between tiles (uses config default if None)
    """
    global _default_tile_config
    if rows is None:
        rows = _tiling_config.grid_rows
    if cols is None:
        cols = _tiling_config.grid_cols
    if overlap is None:
        overlap = _tiling_config.overlap_percent
    _default_tile_config = TileConfig(rows, cols, overlap)
    print(f"Tile config set to: {rows}x{cols} grid with {overlap*100:.0f}% overlap")


def get_tile_config() -> TileConfig:
    """Get the current default tile configuration."""
    return _default_tile_config
    """Get the current default tile configuration."""
    return DEFAULT_TILE_CONFIG
