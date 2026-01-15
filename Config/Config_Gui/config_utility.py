#!/usr/bin/env python3
"""
Vision Configuration Utility
============================

Simple script to view and modify vision system configuration parameters.
Run this script to interactively change settings or use it to generate custom configurations.
"""

import sys
import os
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from Config.vision_config import VisionConfig, get_config, save_config


def print_current_config():
    """Print the current configuration in a readable format."""
    config = get_config()
    
    print("\n" + "="*60)
    print("CURRENT VISION CONFIGURATION")
    print("="*60)
    
    print("\n🎯 YOLO Configuration:")
    print(f"  Model Path:         {config.yolo.model_path}")
    print(f"  Device:             {config.yolo.device}")
    print(f"  Confidence Thresh:  {config.yolo.conf_thresh}")
    print(f"  Image Size:         {config.yolo.imgsz}")
    print(f"  NMS IoU Threshold:  {config.yolo.nms_iou_threshold}")
    print(f"  Target Classes:     {config.yolo.classes}")
    print(f"  Verbose Output:     {config.yolo.verbose}")
    
    print("\n🧩 Tiling Configuration:")
    print(f"  Use Tiled Inference: {config.tiling.use_tiled_inference}")
    print(f"  Grid Size:          {config.tiling.grid_rows} x {config.tiling.grid_cols}")
    print(f"  Overlap Percent:    {config.tiling.overlap_percent * 100:.1f}%")
    print(f"  Merge IoU Thresh:   {config.tiling.merge_iou_threshold}")
    
    print("\n📷 Camera Configuration:")
    print(f"  Primary Index:      {config.camera.camera_index}")
    print(f"  Fallback Index:     {config.camera.fallback_index}")
    print(f"  Resolution:         {config.camera.width} x {config.camera.height}")
    print(f"  FPS:                {config.camera.fps}")
    print(f"  Buffer Size:        {config.camera.buffer_size}")
    print(f"  Codec:              {config.camera.fourcc}")
    
    print("\n⚙️  System Configuration:")
    print(f"  Staleness Threshold: {config.system.staleness_threshold_s}s")
    print(f"  Vision Loop Rate:   {1/config.system.vision_loop_interval:.1f} Hz")
    print(f"  Enable Display:     {config.system.enable_display}")
    print(f"  Show Confidence:    {config.system.show_confidence}")
    print(f"  Show Crosshair:     {config.system.show_crosshair}")
    print(f"  Window Name:        {config.system.window_name}")
    print(f"  BBox Color:         {config.system.bbox_color}")
    print(f"  Crosshair Color:    {config.system.crosshair_color}")
    print()


def quick_presets():
    """Apply common configuration presets."""
    config = get_config()
    
    print("\n🚀 Quick Configuration Presets:")
    print("1. High Performance (Fast detection, lower accuracy)")
    print("2. High Accuracy (Slower detection, better accuracy)")  
    print("3. 4K Camera Setup (High resolution, 3x3 tiling)")
    print("4. Debug Mode (Enable all debug features)")
    print("5. Production Mode (Optimized for deployment)")
    print("0. Cancel")
    
    choice = input("\nSelect preset (0-5): ").strip()
    
    if choice == "1":
        # High Performance
        config.yolo.imgsz = 640
        config.yolo.model_path = "yolov8n.pt"
        config.tiling.use_tiled_inference = False
        config.system.vision_loop_interval = 0.033  # ~30 FPS
        print("✅ Applied High Performance preset")
        
    elif choice == "2":
        # High Accuracy
        config.yolo.imgsz = 1280
        config.yolo.model_path = "yolov8s.pt"
        config.yolo.conf_thresh = 0.4
        config.tiling.use_tiled_inference = True
        config.tiling.grid_rows = 3
        config.tiling.grid_cols = 3
        print("✅ Applied High Accuracy preset")
        
    elif choice == "3":
        # 4K Camera
        config.camera.width = 1920
        config.camera.height = 1080
        config.yolo.imgsz = 1280
        config.tiling.use_tiled_inference = True
        config.tiling.grid_rows = 3
        config.tiling.grid_cols = 3
        config.tiling.overlap_percent = 0.2
        print("✅ Applied 4K Camera Setup preset")
        
    elif choice == "4":
        # Debug Mode
        config.system.print_fps = True
        config.system.print_detections = True
        config.yolo.verbose = True
        config.system.show_confidence = True
        config.system.show_crosshair = True
        print("✅ Applied Debug Mode preset")
        
    elif choice == "5":
        # Production Mode
        config.system.enable_display = False
        config.system.print_fps = False
        config.system.print_detections = False
        config.yolo.verbose = False
        config.system.vision_loop_interval = 0.05
        print("✅ Applied Production Mode preset")
        
    elif choice == "0":
        return False
    else:
        print("❌ Invalid choice")
        return False
        
    return True


def interactive_config():
    """Interactive configuration editor."""
    config = get_config()
    
    while True:
        print("\n🔧 Interactive Configuration Editor:")
        print("1. YOLO Settings")
        print("2. Tiling Settings") 
        print("3. Camera Settings")
        print("4. System Settings")
        print("5. Save & Exit")
        print("0. Exit without saving")
        
        choice = input("\nSelect category (0-5): ").strip()
        
        if choice == "1":
            edit_yolo_settings(config)
        elif choice == "2":
            edit_tiling_settings(config)
        elif choice == "3":
            edit_camera_settings(config)
        elif choice == "4":
            edit_system_settings(config)
        elif choice == "5":
            save_config()
            print("✅ Configuration saved!")
            break
        elif choice == "0":
            print("❌ Exiting without saving changes")
            break
        else:
            print("❌ Invalid choice")


def edit_yolo_settings(config):
    """Edit YOLO-specific settings."""
    print("\n🎯 YOLO Settings:")
    
    # Model selection
    print(f"\nCurrent model: {config.yolo.model_path}")
    models = ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"]
    print("Available models:", ", ".join(models))
    new_model = input("New model (or Enter to keep current): ").strip()
    if new_model and new_model in models:
        config.yolo.model_path = new_model
    
    # Confidence threshold
    new_conf = input(f"Confidence threshold (current: {config.yolo.conf_thresh}): ").strip()
    if new_conf:
        try:
            config.yolo.conf_thresh = float(new_conf)
        except ValueError:
            print("❌ Invalid number")
    
    # Image size
    new_imgsz = input(f"Image size (current: {config.yolo.imgsz}): ").strip()
    if new_imgsz:
        try:
            config.yolo.imgsz = int(new_imgsz)
        except ValueError:
            print("❌ Invalid number")


def edit_tiling_settings(config):
    """Edit tiling-specific settings."""
    print("\n🧩 Tiling Settings:")
    
    # Enable/disable tiling
    current = "enabled" if config.tiling.use_tiled_inference else "disabled"
    toggle = input(f"Tiling is currently {current}. Toggle? (y/n): ").strip().lower()
    if toggle == 'y':
        config.tiling.use_tiled_inference = not config.tiling.use_tiled_inference
    
    if config.tiling.use_tiled_inference:
        # Grid size
        new_rows = input(f"Grid rows (current: {config.tiling.grid_rows}): ").strip()
        if new_rows:
            try:
                config.tiling.grid_rows = int(new_rows)
            except ValueError:
                print("❌ Invalid number")
        
        new_cols = input(f"Grid cols (current: {config.tiling.grid_cols}): ").strip()
        if new_cols:
            try:
                config.tiling.grid_cols = int(new_cols)
            except ValueError:
                print("❌ Invalid number")
        
        # Overlap
        current_overlap = config.tiling.overlap_percent * 100
        new_overlap = input(f"Overlap percentage (current: {current_overlap:.1f}%): ").strip()
        if new_overlap:
            try:
                config.tiling.overlap_percent = float(new_overlap) / 100.0
            except ValueError:
                print("❌ Invalid number")


def edit_camera_settings(config):
    """Edit camera-specific settings."""
    print("\n📷 Camera Settings:")
    
    # Camera index
    new_index = input(f"Camera index (current: {config.camera.camera_index}): ").strip()
    if new_index:
        try:
            config.camera.camera_index = int(new_index)
        except ValueError:
            print("❌ Invalid number")
    
    # Resolution
    new_width = input(f"Width (current: {config.camera.width}): ").strip()
    if new_width:
        try:
            config.camera.width = int(new_width)
        except ValueError:
            print("❌ Invalid number")
            
    new_height = input(f"Height (current: {config.camera.height}): ").strip()
    if new_height:
        try:
            config.camera.height = int(new_height)
        except ValueError:
            print("❌ Invalid number")
    
    # FPS
    new_fps = input(f"FPS (current: {config.camera.fps}): ").strip()
    if new_fps:
        try:
            config.camera.fps = int(new_fps)
        except ValueError:
            print("❌ Invalid number")


def edit_system_settings(config):
    """Edit system-specific settings."""
    print("\n⚙️  System Settings:")
    
    # Display toggle
    current = "enabled" if config.system.enable_display else "disabled"
    toggle = input(f"Display is currently {current}. Toggle? (y/n): ").strip().lower()
    if toggle == 'y':
        config.system.enable_display = not config.system.enable_display
    
    # Staleness threshold
    new_staleness = input(f"Staleness threshold (current: {config.system.staleness_threshold_s}s): ").strip()
    if new_staleness:
        try:
            config.system.staleness_threshold_s = float(new_staleness)
        except ValueError:
            print("❌ Invalid number")


def main():
    """Main configuration utility interface."""
    print("🎯 Vision System Configuration Utility")
    print("="*50)
    
    while True:
        print("\nWhat would you like to do?")
        print("1. View current configuration")
        print("2. Apply quick preset")
        print("3. Interactive configuration editor")
        print("4. Export configuration to file")
        print("5. Import configuration from file")
        print("0. Exit")
        
        choice = input("\nSelect option (0-5): ").strip()
        
        if choice == "1":
            print_current_config()
            
        elif choice == "2":
            if quick_presets():
                save_config()
                print("✅ Preset applied and saved!")
                
        elif choice == "3":
            interactive_config()
            
        elif choice == "4":
            filename = input("Export filename (default: my_vision_config.json): ").strip()
            if not filename:
                filename = "my_vision_config.json"
            config = get_config()
            config.save_to_file(filename)
            print(f"✅ Configuration exported to {filename}")
            
        elif choice == "5":
            filename = input("Import filename: ").strip()
            if os.path.exists(filename):
                try:
                    imported_config = VisionConfig.load_from_file(filename)
                    # Save the imported config as current
                    imported_config.save_to_file(os.path.join(os.path.dirname(__file__), 'vision_config.json'))
                    print(f"✅ Configuration imported from {filename}")
                except Exception as e:
                    print(f"❌ Failed to import: {e}")
            else:
                print("❌ File not found")
                
        elif choice == "0":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()