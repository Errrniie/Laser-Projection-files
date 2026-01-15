"""
Vision System Configuration
==========================

Central configuration file for all vision-related parameters.
Modify values here to adjust YOLO detection, camera settings, tiling, and other vision parameters.
"""

from dataclasses import dataclass
from typing import Optional
import json
import os


@dataclass
class YOLOConfig:
    """YOLO Model Configuration"""
    # Model settings
    model_path: str = "yolov8s.pt"              # Path to YOLO model file (yolov8n.pt, yolov8s.pt, yolov8m.pt, etc.)
    device: str = "cpu"                          # Device for inference ("cpu", "cuda", "mps")
    
    # Detection thresholds
    conf_thresh: float = 0.6                     # Confidence threshold for detections (0.0-1.0)
    nms_iou_threshold: float = 0.5               # IoU threshold for Non-Maximum Suppression
    
    # Image processing
    imgsz: int = 1280                           # Input image size for YOLO (640, 960, 1280, etc.)
    classes: list = None                         # Classes to detect (None for all, [0] for person only)
    verbose: bool = False                        # Enable verbose YOLO output
    
    def __post_init__(self):
        if self.classes is None:
            self.classes = [0]  # Person class only by default


@dataclass 
class TilingConfig:
    """Tiled Inference Configuration"""
    # Enable/disable tiling
    use_tiled_inference: bool = True             # Set to False to disable tiling completely
    
    # Grid configuration
    grid_rows: int = 2                          # Number of tile rows
    grid_cols: int = 2                          # Number of tile columns
    overlap_percent: float = 0.15               # Overlap between tiles (0.0-0.5)
    
    # NMS settings for merging tiles
    merge_iou_threshold: float = 0.5             # IoU threshold for merging detections across tiles
    
    def __post_init__(self):
        if not 0.0 <= self.overlap_percent <= 0.5:
            raise ValueError("overlap_percent must be between 0.0 and 0.5")
        if self.grid_rows < 1 or self.grid_cols < 1:
            raise ValueError("Grid dimensions must be at least 1x1")


@dataclass
class CameraConfig:
    """Camera Hardware Configuration"""
    # Camera selection
    camera_index: int = 4                        # Camera device index (0, 1, 2, 4, etc.)
    fallback_index: int = 0                      # Fallback camera index if primary fails
    
    # Resolution settings
    width: int = 640                            # Camera capture width
    height: int = 480                           # Camera capture height
    
    # Performance settings  
    fps: int = 30                               # Target frames per second
    buffer_size: int = 1                        # Camera buffer size (lower = less latency)
    fourcc: str = "MJPG"                        # Video codec fourcc
    
    # OpenCV backend
    backend: int = None                         # cv2.CAP_V4L2, cv2.CAP_DSHOW, etc. (None for auto)
    
    def __post_init__(self):
        # Set default backend based on common setups
        if self.backend is None:
            import cv2
            # Use V4L2 on Linux, DirectShow on Windows
            try:
                self.backend = cv2.CAP_V4L2  # Linux
            except AttributeError:
                try:
                    self.backend = cv2.CAP_DSHOW  # Windows
                except AttributeError:
                    self.backend = cv2.CAP_ANY  # Fallback


@dataclass
class VisionSystemConfig:
    """Overall Vision System Configuration"""
    # Threading and performance
    staleness_threshold_s: float = 0.5          # Max age of detection before considered stale (seconds)
    vision_loop_interval: float = 0.05          # Vision processing interval (0.05 = 20Hz)
    display_queue_maxsize: int = 1              # Max frames queued for display
    
    # Display settings
    window_name: str = "Goose Vision"           # OpenCV window name
    show_confidence: bool = True                # Show confidence scores on detections
    show_crosshair: bool = True                 # Show center crosshair
    bbox_color: tuple = (0, 255, 0)            # Bounding box color (BGR)
    crosshair_color: tuple = (255, 0, 0)       # Crosshair color (BGR)
    bbox_thickness: int = 2                     # Bounding box line thickness
    crosshair_size: int = 20                   # Crosshair marker size
    
    # Debug options
    enable_display: bool = True                 # Enable visual display window
    print_fps: bool = False                     # Print FPS information
    print_detections: bool = False              # Print detection results


@dataclass
class VisionConfig:
    """Master configuration class containing all vision settings"""
    yolo: YOLOConfig = None
    tiling: TilingConfig = None
    camera: CameraConfig = None
    system: VisionSystemConfig = None
    
    def __post_init__(self):
        if self.yolo is None:
            self.yolo = YOLOConfig()
        if self.tiling is None:
            self.tiling = TilingConfig()
        if self.camera is None:
            self.camera = CameraConfig()
        if self.system is None:
            self.system = VisionSystemConfig()
    
    def save_to_file(self, filepath: str):
        """Save configuration to JSON file"""
        config_dict = {
            'yolo': {
                'model_path': self.yolo.model_path,
                'device': self.yolo.device,
                'conf_thresh': self.yolo.conf_thresh,
                'nms_iou_threshold': self.yolo.nms_iou_threshold,
                'imgsz': self.yolo.imgsz,
                'classes': self.yolo.classes,
                'verbose': self.yolo.verbose
            },
            'tiling': {
                'use_tiled_inference': self.tiling.use_tiled_inference,
                'grid_rows': self.tiling.grid_rows,
                'grid_cols': self.tiling.grid_cols,
                'overlap_percent': self.tiling.overlap_percent,
                'merge_iou_threshold': self.tiling.merge_iou_threshold
            },
            'camera': {
                'camera_index': self.camera.camera_index,
                'fallback_index': self.camera.fallback_index,
                'width': self.camera.width,
                'height': self.camera.height,
                'fps': self.camera.fps,
                'buffer_size': self.camera.buffer_size,
                'fourcc': self.camera.fourcc
            },
            'system': {
                'staleness_threshold_s': self.system.staleness_threshold_s,
                'vision_loop_interval': self.system.vision_loop_interval,
                'display_queue_maxsize': self.system.display_queue_maxsize,
                'window_name': self.system.window_name,
                'show_confidence': self.system.show_confidence,
                'show_crosshair': self.system.show_crosshair,
                'bbox_color': self.system.bbox_color,
                'crosshair_color': self.system.crosshair_color,
                'bbox_thickness': self.system.bbox_thickness,
                'crosshair_size': self.system.crosshair_size,
                'enable_display': self.system.enable_display,
                'print_fps': self.system.print_fps,
                'print_detections': self.system.print_detections
            }
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'VisionConfig':
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        
        # Create config objects from loaded data
        yolo_config = YOLOConfig(**config_dict.get('yolo', {}))
        tiling_config = TilingConfig(**config_dict.get('tiling', {}))
        camera_config = CameraConfig(**config_dict.get('camera', {}))
        system_config = VisionSystemConfig(**config_dict.get('system', {}))
        
        return cls(
            yolo=yolo_config,
            tiling=tiling_config, 
            camera=camera_config,
            system=system_config
        )


# Global configuration instance
_config = None

def get_config() -> VisionConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        config_path = os.path.join(os.path.dirname(__file__), 'vision_config.json')
        if os.path.exists(config_path):
            _config = VisionConfig.load_from_file(config_path)
        else:
            _config = VisionConfig()
            # Save default config
            _config.save_to_file(config_path)
    return _config

def reload_config():
    """Reload configuration from file"""
    global _config
    _config = None
    return get_config()

def save_config():
    """Save current configuration to file"""
    config = get_config()
    config_path = os.path.join(os.path.dirname(__file__), 'vision_config.json')
    config.save_to_file(config_path)


# Convenience functions for backward compatibility
def get_yolo_config() -> YOLOConfig:
    """Get YOLO configuration"""
    return get_config().yolo

def get_tiling_config() -> TilingConfig:
    """Get tiling configuration"""
    return get_config().tiling

def get_camera_config() -> CameraConfig:
    """Get camera configuration"""
    return get_config().camera

def get_system_config() -> VisionSystemConfig:
    """Get system configuration"""
    return get_config().system


if __name__ == "__main__":
    # Create and save default configuration file
    config = VisionConfig()
    config.save_to_file('vision_config.json')
    print("Default configuration saved to vision_config.json")
    
    # Example of modifying configuration
    config.yolo.imgsz = 960
    config.camera.width = 1920
    config.camera.height = 1080
    config.tiling.grid_rows = 3
    config.tiling.grid_cols = 3
    
    print("\nExample modified configuration:")
    print(f"YOLO image size: {config.yolo.imgsz}")
    print(f"Camera resolution: {config.camera.width}x{config.camera.height}")
    print(f"Tiling grid: {config.tiling.grid_rows}x{config.tiling.grid_cols}")