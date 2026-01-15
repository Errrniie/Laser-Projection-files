# Vision System Configuration

This folder contains the centralized configuration system for the GooseProject vision system.

## Files

### `vision_config.py`
The main configuration module containing:
- **YOLOConfig**: YOLO model settings (model path, device, thresholds, image size)
- **TilingConfig**: Tiled inference settings (grid size, overlap, NMS thresholds)
- **CameraConfig**: Camera hardware settings (resolution, FPS, device indices)
- **VisionSystemConfig**: System-level settings (display options, performance tuning)

### `vision_config.json`
Default configuration file with all parameter values. This file is automatically loaded when the vision system starts.

### `config_gui.py`
**NEW!** Graphical user interface for configuration management. Provides an intuitive window-based interface with:
- Tabbed organization of settings (YOLO, Tiling, Camera, System, Presets)
- Interactive controls (sliders, checkboxes, dropdowns)
- Real-time value updates
- Quick preset buttons
- Save/load/import/export functionality

### `config_utility.py`
Command-line utility for viewing and modifying configuration settings (original text-based interface).

### `launch_config.py`
Simple launcher script that lets you choose between GUI or command-line interfaces.

## Usage

### Quick Start - GUI Interface (Recommended)
```bash
cd Config
python config_gui.py
```
Or use the launcher:
```bash
cd Config
python launch_config.py
```

The GUI provides:
- **📋 Tabbed Interface**: Organized settings by category (YOLO, Tiling, Camera, System)
- **🎚️ Interactive Controls**: Sliders for thresholds, spinboxes for numbers, checkboxes for booleans
- **🚀 Quick Presets**: One-click application of common configurations
- **💾 File Operations**: Save, load, import, and export configurations
- **🔄 Real-time Updates**: See changes immediately with live value displays

### Command Line Interface
```bash
cd Config
python config_utility.py
```
This opens the original text-based menu interface.

### Configuration Changes
```bash
cd Config
python config_utility.py
```
This opens an interactive menu where you can:
- View current settings
- Apply quick presets (High Performance, High Accuracy, 4K Setup, etc.)
- Edit individual parameters
- Export/import configuration files

### Programmatic Configuration
```python
from Config.vision_config import get_config

# Get current configuration
config = get_config()

# Modify settings
config.yolo.imgsz = 960
config.camera.width = 1920
config.camera.height = 1080

# Save changes
from Config.vision_config import save_config
save_config()
```

### Configuration in Code
All vision modules now automatically use the configuration system:

```python
# In your code, these now use config values automatically:
from YoloModel.Detection import detect_human  # Uses config IMGSZ, CONF_THRESH, etc.
from YoloModel.CameraThread import CameraThread  # Uses config camera settings
```

## Key Configuration Parameters

### YOLO Detection
- **imgsz**: Input image size (640=fast, 1280=accurate)
- **conf_thresh**: Confidence threshold for detections (0.0-1.0)
- **model_path**: YOLO model file (yolov8n.pt, yolov8s.pt, etc.)
- **device**: Processing device ("cpu", "cuda", "mps")

### Tiling (for high-resolution frames)
- **use_tiled_inference**: Enable/disable tiling
- **grid_rows/grid_cols**: Tile grid dimensions
- **overlap_percent**: Overlap between tiles (0.0-0.5)

### Camera Settings  
- **camera_index**: Primary camera device index
- **fallback_index**: Backup camera if primary fails
- **width/height**: Capture resolution
- **fps**: Target frames per second

### Performance Tuning
- **staleness_threshold_s**: Max age of valid detections
- **vision_loop_interval**: Processing rate (0.033≈30Hz, 0.05=20Hz)
- **enable_display**: Show/hide visual display window

## Quick Presets

The utility includes several presets:

1. **High Performance**: Fast detection (YOLOv8n, 640px, no tiling)
2. **High Accuracy**: Accurate detection (YOLOv8s, 1280px, 3x3 tiling)
3. **4K Camera Setup**: High resolution with optimal tiling
4. **Debug Mode**: Enable all debugging features
5. **Production Mode**: Optimized for deployment (no display)

## Migration from Hardcoded Values

All hardcoded constants have been replaced:
- `IMGSZ = 1280` → `config.yolo.imgsz`
- `CONF_THRESH = 0.6` → `config.yolo.conf_thresh`  
- `CameraThread(index=4, width=640, height=480, fps=30)` → Uses config defaults
- Tiling parameters → `config.tiling.*`
- Display colors/settings → `config.system.*`

## Tips

- **Start with presets**: Use the utility to apply a preset close to your needs, then fine-tune
- **Test changes**: Run the vision system after config changes to verify performance
- **Backup configs**: Export your working configurations for easy restoration
- **Environment-specific**: Create different config files for different deployment environments