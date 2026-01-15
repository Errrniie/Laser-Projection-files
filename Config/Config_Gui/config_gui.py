#!/usr/bin/env python3
"""
Vision Configuration GUI
========================

Graphical user interface for configuring vision system parameters.
Provides an intuitive way to view and modify all vision settings with real-time updates.
"""

import sys
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from Config.vision_config import VisionConfig, get_config, save_config, reload_config


class VisionConfigGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GooseProject Vision Configuration")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Load configuration
        self.config = get_config()
        
        # Create main interface
        self.create_widgets()
        self.load_current_values()
        
    def create_widgets(self):
        """Create the main GUI interface"""
        # Create main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Vision System Configuration", 
                               font=('Helvetica', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create tabs
        self.create_yolo_tab()
        self.create_tiling_tab()
        self.create_camera_tab()
        self.create_system_tab()
        self.create_presets_tab()
        
        # Bottom button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0), sticky=(tk.W, tk.E))
        button_frame.columnconfigure(0, weight=1)
        
        # Action buttons
        btn_frame = ttk.Frame(button_frame)
        btn_frame.grid(row=0, column=0)
        
        ttk.Button(btn_frame, text="💾 Save Configuration", 
                  command=self.save_config, width=20).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="🔄 Reload", 
                  command=self.reload_config, width=15).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="📤 Export", 
                  command=self.export_config, width=15).grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="📥 Import", 
                  command=self.import_config, width=15).grid(row=0, column=3, padx=5)
    
    def create_yolo_tab(self):
        """Create YOLO configuration tab"""
        self.yolo_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.yolo_frame, text="🎯 YOLO")
        
        # Create scrollable frame
        canvas = tk.Canvas(self.yolo_frame)
        scrollbar = ttk.Scrollbar(self.yolo_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # YOLO settings
        row = 0
        
        # Model Path
        ttk.Label(scrollable_frame, text="Model Path:", font=('Helvetica', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.yolo_model_var = tk.StringVar()
        model_combo = ttk.Combobox(scrollable_frame, textvariable=self.yolo_model_var,
                                  values=["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"])
        model_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        row += 1
        
        # Device
        ttk.Label(scrollable_frame, text="Device:", font=('Helvetica', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.yolo_device_var = tk.StringVar()
        device_combo = ttk.Combobox(scrollable_frame, textvariable=self.yolo_device_var,
                                   values=["cpu", "cuda", "mps"])
        device_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        row += 1
        
        # Confidence Threshold
        ttk.Label(scrollable_frame, text="Confidence Threshold:", font=('Helvetica', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.yolo_conf_var = tk.DoubleVar()
        conf_scale = ttk.Scale(scrollable_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
                              variable=self.yolo_conf_var, command=self.update_conf_label)
        conf_scale.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        self.conf_label = ttk.Label(scrollable_frame, text="0.6")
        self.conf_label.grid(row=row, column=2, pady=5, padx=5)
        row += 1
        
        # Image Size
        ttk.Label(scrollable_frame, text="Image Size:", font=('Helvetica', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.yolo_imgsz_var = tk.IntVar()
        imgsz_combo = ttk.Combobox(scrollable_frame, textvariable=self.yolo_imgsz_var,
                                  values=[320, 640, 960, 1280, 1536])
        imgsz_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        row += 1
        
        # NMS IoU Threshold
        ttk.Label(scrollable_frame, text="NMS IoU Threshold:", font=('Helvetica', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.yolo_nms_var = tk.DoubleVar()
        nms_scale = ttk.Scale(scrollable_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
                             variable=self.yolo_nms_var, command=self.update_nms_label)
        nms_scale.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        self.nms_label = ttk.Label(scrollable_frame, text="0.5")
        self.nms_label.grid(row=row, column=2, pady=5, padx=5)
        row += 1
        
        # Verbose
        self.yolo_verbose_var = tk.BooleanVar()
        ttk.Checkbutton(scrollable_frame, text="Verbose Output", 
                       variable=self.yolo_verbose_var).grid(row=row, column=0, columnspan=2, 
                                                           sticky=tk.W, pady=5, padx=10)
        
        scrollable_frame.columnconfigure(1, weight=1)
    
    def create_tiling_tab(self):
        """Create Tiling configuration tab"""
        self.tiling_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tiling_frame, text="🧩 Tiling")
        
        row = 0
        
        # Use Tiled Inference
        self.tiling_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(self.tiling_frame, text="Enable Tiled Inference", 
                       variable=self.tiling_enabled_var,
                       command=self.toggle_tiling_options).grid(row=row, column=0, columnspan=2, 
                                                               sticky=tk.W, pady=10, padx=10)
        row += 1
        
        # Tiling options frame
        self.tiling_options_frame = ttk.LabelFrame(self.tiling_frame, text="Tiling Settings", padding="10")
        self.tiling_options_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), 
                                      pady=10, padx=10)
        row += 1
        
        # Grid Rows
        ttk.Label(self.tiling_options_frame, text="Grid Rows:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.tiling_rows_var = tk.IntVar()
        ttk.Spinbox(self.tiling_options_frame, from_=1, to=10, textvariable=self.tiling_rows_var,
                   width=10).grid(row=0, column=1, pady=5, padx=10)
        
        # Grid Columns
        ttk.Label(self.tiling_options_frame, text="Grid Columns:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.tiling_cols_var = tk.IntVar()
        ttk.Spinbox(self.tiling_options_frame, from_=1, to=10, textvariable=self.tiling_cols_var,
                   width=10).grid(row=1, column=1, pady=5, padx=10)
        
        # Overlap Percentage
        ttk.Label(self.tiling_options_frame, text="Overlap Percentage:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.tiling_overlap_var = tk.DoubleVar()
        overlap_scale = ttk.Scale(self.tiling_options_frame, from_=0.0, to=0.5, orient=tk.HORIZONTAL,
                                 variable=self.tiling_overlap_var, command=self.update_overlap_label)
        overlap_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        self.overlap_label = ttk.Label(self.tiling_options_frame, text="15%")
        self.overlap_label.grid(row=2, column=2, pady=5, padx=5)
        
        # Merge IoU Threshold
        ttk.Label(self.tiling_options_frame, text="Merge IoU Threshold:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.tiling_merge_iou_var = tk.DoubleVar()
        merge_scale = ttk.Scale(self.tiling_options_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
                               variable=self.tiling_merge_iou_var, command=self.update_merge_iou_label)
        merge_scale.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=10)
        self.merge_iou_label = ttk.Label(self.tiling_options_frame, text="0.5")
        self.merge_iou_label.grid(row=3, column=2, pady=5, padx=5)
        
        self.tiling_options_frame.columnconfigure(1, weight=1)
        self.tiling_frame.columnconfigure(0, weight=1)
    
    def create_camera_tab(self):
        """Create Camera configuration tab"""
        self.camera_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.camera_frame, text="📷 Camera")
        
        row = 0
        
        # Camera Index
        ttk.Label(self.camera_frame, text="Primary Camera Index:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.camera_index_var = tk.IntVar()
        ttk.Spinbox(self.camera_frame, from_=0, to=10, textvariable=self.camera_index_var,
                   width=10).grid(row=row, column=1, pady=5, padx=10)
        row += 1
        
        # Fallback Index
        ttk.Label(self.camera_frame, text="Fallback Camera Index:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.camera_fallback_var = tk.IntVar()
        ttk.Spinbox(self.camera_frame, from_=0, to=10, textvariable=self.camera_fallback_var,
                   width=10).grid(row=row, column=1, pady=5, padx=10)
        row += 1
        
        # Resolution
        ttk.Label(self.camera_frame, text="Width:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.camera_width_var = tk.IntVar()
        width_combo = ttk.Combobox(self.camera_frame, textvariable=self.camera_width_var,
                                  values=[320, 640, 1280, 1920, 3840])
        width_combo.grid(row=row, column=1, pady=5, padx=10)
        row += 1
        
        ttk.Label(self.camera_frame, text="Height:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.camera_height_var = tk.IntVar()
        height_combo = ttk.Combobox(self.camera_frame, textvariable=self.camera_height_var,
                                   values=[240, 480, 720, 1080, 2160])
        height_combo.grid(row=row, column=1, pady=5, padx=10)
        row += 1
        
        # FPS
        ttk.Label(self.camera_frame, text="FPS:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.camera_fps_var = tk.IntVar()
        ttk.Spinbox(self.camera_frame, from_=1, to=120, textvariable=self.camera_fps_var,
                   width=10).grid(row=row, column=1, pady=5, padx=10)
        row += 1
        
        # Buffer Size
        ttk.Label(self.camera_frame, text="Buffer Size:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.camera_buffer_var = tk.IntVar()
        ttk.Spinbox(self.camera_frame, from_=1, to=10, textvariable=self.camera_buffer_var,
                   width=10).grid(row=row, column=1, pady=5, padx=10)
        row += 1
        
        # Codec
        ttk.Label(self.camera_frame, text="Codec:").grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.camera_fourcc_var = tk.StringVar()
        fourcc_combo = ttk.Combobox(self.camera_frame, textvariable=self.camera_fourcc_var,
                                   values=["MJPG", "YUYV", "H264"])
        fourcc_combo.grid(row=row, column=1, pady=5, padx=10)
    
    def create_system_tab(self):
        """Create System configuration tab"""
        self.system_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.system_frame, text="⚙️ System")
        
        row = 0
        
        # Display Settings
        display_frame = ttk.LabelFrame(self.system_frame, text="Display Settings", padding="10")
        display_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10, padx=10)
        row += 1
        
        self.system_enable_display_var = tk.BooleanVar()
        ttk.Checkbutton(display_frame, text="Enable Display Window", 
                       variable=self.system_enable_display_var).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.system_show_confidence_var = tk.BooleanVar()
        ttk.Checkbutton(display_frame, text="Show Confidence Scores", 
                       variable=self.system_show_confidence_var).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.system_show_crosshair_var = tk.BooleanVar()
        ttk.Checkbutton(display_frame, text="Show Center Crosshair", 
                       variable=self.system_show_crosshair_var).grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # Performance Settings
        perf_frame = ttk.LabelFrame(self.system_frame, text="Performance Settings", padding="10")
        perf_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10, padx=10)
        row += 1
        
        ttk.Label(perf_frame, text="Staleness Threshold (s):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.system_staleness_var = tk.DoubleVar()
        ttk.Spinbox(perf_frame, from_=0.1, to=5.0, increment=0.1, textvariable=self.system_staleness_var,
                   width=10).grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Label(perf_frame, text="Vision Loop Interval (s):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.system_loop_interval_var = tk.DoubleVar()
        ttk.Spinbox(perf_frame, from_=0.01, to=1.0, increment=0.01, textvariable=self.system_loop_interval_var,
                   width=10).grid(row=1, column=1, pady=5, padx=10)
        
        # Debug Settings
        debug_frame = ttk.LabelFrame(self.system_frame, text="Debug Settings", padding="10")
        debug_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10, padx=10)
        
        self.system_print_fps_var = tk.BooleanVar()
        ttk.Checkbutton(debug_frame, text="Print FPS Information", 
                       variable=self.system_print_fps_var).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.system_print_detections_var = tk.BooleanVar()
        ttk.Checkbutton(debug_frame, text="Print Detection Results", 
                       variable=self.system_print_detections_var).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.system_frame.columnconfigure(0, weight=1)
    
    def create_presets_tab(self):
        """Create Presets tab"""
        self.presets_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.presets_frame, text="🚀 Presets")
        
        # Description
        desc_label = ttk.Label(self.presets_frame, 
                              text="Quick configuration presets for common use cases:",
                              font=('Helvetica', 12))
        desc_label.pack(pady=20)
        
        # Preset buttons
        presets = [
            ("⚡ High Performance", "Fast detection (YOLOv8n, 640px, no tiling)", self.apply_high_performance),
            ("🎯 High Accuracy", "Accurate detection (YOLOv8s, 1280px, 3x3 tiling)", self.apply_high_accuracy),
            ("📺 4K Camera Setup", "High resolution with optimal tiling", self.apply_4k_setup),
            ("🐛 Debug Mode", "Enable all debugging features", self.apply_debug_mode),
            ("🏭 Production Mode", "Optimized for deployment (no display)", self.apply_production_mode)
        ]
        
        for title, desc, command in presets:
            frame = ttk.Frame(self.presets_frame)
            frame.pack(fill=tk.X, padx=20, pady=10)
            
            btn = ttk.Button(frame, text=title, command=command, width=25)
            btn.pack(side=tk.LEFT, padx=(0, 10))
            
            desc_label = ttk.Label(frame, text=desc, foreground="gray")
            desc_label.pack(side=tk.LEFT)
    
    def load_current_values(self):
        """Load current configuration values into the GUI"""
        # YOLO settings
        self.yolo_model_var.set(self.config.yolo.model_path)
        self.yolo_device_var.set(self.config.yolo.device)
        self.yolo_conf_var.set(self.config.yolo.conf_thresh)
        self.yolo_imgsz_var.set(self.config.yolo.imgsz)
        self.yolo_nms_var.set(self.config.yolo.nms_iou_threshold)
        self.yolo_verbose_var.set(self.config.yolo.verbose)
        
        # Tiling settings
        self.tiling_enabled_var.set(self.config.tiling.use_tiled_inference)
        self.tiling_rows_var.set(self.config.tiling.grid_rows)
        self.tiling_cols_var.set(self.config.tiling.grid_cols)
        self.tiling_overlap_var.set(self.config.tiling.overlap_percent)
        self.tiling_merge_iou_var.set(self.config.tiling.merge_iou_threshold)
        
        # Camera settings
        self.camera_index_var.set(self.config.camera.camera_index)
        self.camera_fallback_var.set(self.config.camera.fallback_index)
        self.camera_width_var.set(self.config.camera.width)
        self.camera_height_var.set(self.config.camera.height)
        self.camera_fps_var.set(self.config.camera.fps)
        self.camera_buffer_var.set(self.config.camera.buffer_size)
        self.camera_fourcc_var.set(self.config.camera.fourcc)
        
        # System settings
        self.system_enable_display_var.set(self.config.system.enable_display)
        self.system_show_confidence_var.set(self.config.system.show_confidence)
        self.system_show_crosshair_var.set(self.config.system.show_crosshair)
        self.system_staleness_var.set(self.config.system.staleness_threshold_s)
        self.system_loop_interval_var.set(self.config.system.vision_loop_interval)
        self.system_print_fps_var.set(self.config.system.print_fps)
        self.system_print_detections_var.set(self.config.system.print_detections)
        
        # Update labels
        self.update_conf_label()
        self.update_nms_label()
        self.update_overlap_label()
        self.update_merge_iou_label()
        self.toggle_tiling_options()
    
    def update_config_from_gui(self):
        """Update configuration object from GUI values"""
        # YOLO settings
        self.config.yolo.model_path = self.yolo_model_var.get()
        self.config.yolo.device = self.yolo_device_var.get()
        self.config.yolo.conf_thresh = self.yolo_conf_var.get()
        self.config.yolo.imgsz = self.yolo_imgsz_var.get()
        self.config.yolo.nms_iou_threshold = self.yolo_nms_var.get()
        self.config.yolo.verbose = self.yolo_verbose_var.get()
        
        # Tiling settings
        self.config.tiling.use_tiled_inference = self.tiling_enabled_var.get()
        self.config.tiling.grid_rows = self.tiling_rows_var.get()
        self.config.tiling.grid_cols = self.tiling_cols_var.get()
        self.config.tiling.overlap_percent = self.tiling_overlap_var.get()
        self.config.tiling.merge_iou_threshold = self.tiling_merge_iou_var.get()
        
        # Camera settings
        self.config.camera.camera_index = self.camera_index_var.get()
        self.config.camera.fallback_index = self.camera_fallback_var.get()
        self.config.camera.width = self.camera_width_var.get()
        self.config.camera.height = self.camera_height_var.get()
        self.config.camera.fps = self.camera_fps_var.get()
        self.config.camera.buffer_size = self.camera_buffer_var.get()
        self.config.camera.fourcc = self.camera_fourcc_var.get()
        
        # System settings
        self.config.system.enable_display = self.system_enable_display_var.get()
        self.config.system.show_confidence = self.system_show_confidence_var.get()
        self.config.system.show_crosshair = self.system_show_crosshair_var.get()
        self.config.system.staleness_threshold_s = self.system_staleness_var.get()
        self.config.system.vision_loop_interval = self.system_loop_interval_var.get()
        self.config.system.print_fps = self.system_print_fps_var.get()
        self.config.system.print_detections = self.system_print_detections_var.get()
    
    # Event handlers
    def update_conf_label(self, *args):
        self.conf_label.config(text=f"{self.yolo_conf_var.get():.2f}")
    
    def update_nms_label(self, *args):
        self.nms_label.config(text=f"{self.yolo_nms_var.get():.2f}")
    
    def update_overlap_label(self, *args):
        self.overlap_label.config(text=f"{self.tiling_overlap_var.get()*100:.0f}%")
    
    def update_merge_iou_label(self, *args):
        self.merge_iou_label.config(text=f"{self.tiling_merge_iou_var.get():.2f}")
    
    def toggle_tiling_options(self):
        state = 'normal' if self.tiling_enabled_var.get() else 'disabled'
        for widget in self.tiling_options_frame.winfo_children():
            if isinstance(widget, (ttk.Scale, ttk.Spinbox)):
                widget.config(state=state)
    
    # Action handlers
    def save_config(self):
        try:
            self.update_config_from_gui()
            save_config()
            messagebox.showinfo("Success", "Configuration saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration:\n{e}")
    
    def reload_config(self):
        try:
            self.config = reload_config()
            self.load_current_values()
            messagebox.showinfo("Success", "Configuration reloaded from file!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reload configuration:\n{e}")
    
    def export_config(self):
        filename = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.update_config_from_gui()
                self.config.save_to_file(filename)
                messagebox.showinfo("Success", f"Configuration exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export configuration:\n{e}")
    
    def import_config(self):
        filename = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.config = VisionConfig.load_from_file(filename)
                self.load_current_values()
                messagebox.showinfo("Success", f"Configuration imported from {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import configuration:\n{e}")
    
    # Preset handlers
    def apply_high_performance(self):
        self.yolo_model_var.set("yolov8n.pt")
        self.yolo_imgsz_var.set(640)
        self.tiling_enabled_var.set(False)
        self.system_loop_interval_var.set(0.033)
        self.toggle_tiling_options()
        messagebox.showinfo("Preset Applied", "High Performance preset applied!")
    
    def apply_high_accuracy(self):
        self.yolo_model_var.set("yolov8s.pt")
        self.yolo_imgsz_var.set(1280)
        self.yolo_conf_var.set(0.4)
        self.tiling_enabled_var.set(True)
        self.tiling_rows_var.set(3)
        self.tiling_cols_var.set(3)
        self.toggle_tiling_options()
        messagebox.showinfo("Preset Applied", "High Accuracy preset applied!")
    
    def apply_4k_setup(self):
        self.camera_width_var.set(1920)
        self.camera_height_var.set(1080)
        self.yolo_imgsz_var.set(1280)
        self.tiling_enabled_var.set(True)
        self.tiling_rows_var.set(3)
        self.tiling_cols_var.set(3)
        self.tiling_overlap_var.set(0.2)
        self.toggle_tiling_options()
        messagebox.showinfo("Preset Applied", "4K Camera Setup preset applied!")
    
    def apply_debug_mode(self):
        self.system_print_fps_var.set(True)
        self.system_print_detections_var.set(True)
        self.yolo_verbose_var.set(True)
        self.system_show_confidence_var.set(True)
        self.system_show_crosshair_var.set(True)
        messagebox.showinfo("Preset Applied", "Debug Mode preset applied!")
    
    def apply_production_mode(self):
        self.system_enable_display_var.set(False)
        self.system_print_fps_var.set(False)
        self.system_print_detections_var.set(False)
        self.yolo_verbose_var.set(False)
        self.system_loop_interval_var.set(0.05)
        messagebox.showinfo("Preset Applied", "Production Mode preset applied!")
    
    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()


def main():
    """Launch the configuration GUI"""
    try:
        app = VisionConfigGUI()
        app.run()
    except Exception as e:
        print(f"Error starting GUI: {e}")
        messagebox.showerror("Error", f"Failed to start configuration GUI:\n{e}")


if __name__ == "__main__":
    main()