# Distance/GUI.py
"""
GUI interface for the Distance Calibration System.
Provides a window-based interface with buttons for all calibration operations.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sys
import os
import threading

# Adjust the Python path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Distance.Storage import (
    list_calibrations, get_calibration, get_calibration_points,
    delete_calibration, get_test_results, get_detection_coverage,
    clear_test_results
)
from Distance.Model import load_model
from Distance.Calibration import VideoCalibrator
from Distance.Test import run_video_test, test_model_live, run_detection_coverage_analysis


class CalibrationManagerGUI:
    """Main GUI window for the Distance Calibration Manager."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Distance Calibration Manager")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'))
        self.style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))
        self.style.configure('Action.TButton', font=('Helvetica', 11), padding=10)
        
        self._create_widgets()
        self._refresh_calibration_list()
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Distance Calibration Manager", style='Title.TLabel')
        title_label.pack(pady=(0, 15))
        
        # Create left and right panes
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left pane - Calibration list
        left_frame = ttk.Frame(paned, padding="5")
        paned.add(left_frame, weight=2)
        
        list_label = ttk.Label(left_frame, text="Calibrations", style='Header.TLabel')
        list_label.pack(anchor=tk.W)
        
        # Treeview for calibrations
        columns = ('name', 'zoom', 'points', 'type')
        self.cal_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=12)
        
        self.cal_tree.heading('name', text='Name')
        self.cal_tree.heading('zoom', text='Zoom')
        self.cal_tree.heading('points', text='Points')
        self.cal_tree.heading('type', text='Type')
        
        self.cal_tree.column('name', width=150)
        self.cal_tree.column('zoom', width=70)
        self.cal_tree.column('points', width=60)
        self.cal_tree.column('type', width=80)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.cal_tree.yview)
        self.cal_tree.configure(yscrollcommand=scrollbar.set)
        
        self.cal_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.cal_tree.bind('<<TreeviewSelect>>', self._on_calibration_select)
        self.cal_tree.bind('<Double-1>', lambda e: self._view_details())
        
        # Right pane - Actions
        right_frame = ttk.Frame(paned, padding="5")
        paned.add(right_frame, weight=1)
        
        # Action buttons frame
        actions_label = ttk.Label(right_frame, text="Actions", style='Header.TLabel')
        actions_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Create calibration section
        create_frame = ttk.LabelFrame(right_frame, text="Create New", padding="10")
        create_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_video_cal = ttk.Button(create_frame, text="📹 Video Calibration", 
                                   command=self._create_video_calibration, style='Action.TButton')
        btn_video_cal.pack(fill=tk.X, pady=2)
        
        btn_live_cal = ttk.Button(create_frame, text="📷 Live Camera Calibration", 
                                  command=self._create_live_calibration, style='Action.TButton')
        btn_live_cal.pack(fill=tk.X, pady=2)
        
        # Test section
        test_frame = ttk.LabelFrame(right_frame, text="Test Selected", padding="10")
        test_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_test_video = ttk.Button(test_frame, text="🎬 Test with Video", 
                                    command=self._test_video, style='Action.TButton')
        btn_test_video.pack(fill=tk.X, pady=2)
        
        btn_test_live = ttk.Button(test_frame, text="📷 Test with Live Camera", 
                                   command=self._test_live, style='Action.TButton')
        btn_test_live.pack(fill=tk.X, pady=2)
        
        btn_analyze = ttk.Button(test_frame, text="📊 Analyze Detection Coverage", 
                                 command=self._analyze_coverage, style='Action.TButton')
        btn_analyze.pack(fill=tk.X, pady=2)
        
        # View section
        view_frame = ttk.LabelFrame(right_frame, text="View", padding="10")
        view_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_details = ttk.Button(view_frame, text="📋 View Details", 
                                 command=self._view_details, style='Action.TButton')
        btn_details.pack(fill=tk.X, pady=2)
        
        btn_results = ttk.Button(view_frame, text="📈 View Test Results", 
                                 command=self._view_test_results, style='Action.TButton')
        btn_results.pack(fill=tk.X, pady=2)
        
        # Manage section
        manage_frame = ttk.LabelFrame(right_frame, text="Manage", padding="10")
        manage_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_delete = ttk.Button(manage_frame, text="🗑️ Delete Calibration", 
                                command=self._delete_calibration, style='Action.TButton')
        btn_delete.pack(fill=tk.X, pady=2)
        
        btn_clear_tests = ttk.Button(manage_frame, text="🧹 Clear Test Results", 
                                     command=self._clear_test_results, style='Action.TButton')
        btn_clear_tests.pack(fill=tk.X, pady=2)
        
        btn_refresh = ttk.Button(manage_frame, text="🔄 Refresh List", 
                                 command=self._refresh_calibration_list, style='Action.TButton')
        btn_refresh.pack(fill=tk.X, pady=2)
        
        # Status bar at bottom
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(10, 0))
    
    def _refresh_calibration_list(self):
        """Refresh the calibration list."""
        # Clear existing items
        for item in self.cal_tree.get_children():
            self.cal_tree.delete(item)
        
        # Load calibrations
        calibrations = list_calibrations()
        
        for cal in calibrations:
            self.cal_tree.insert('', tk.END, values=(
                cal['name'],
                cal['zoom_label'],
                cal['num_points'],
                cal['source_type']
            ))
        
        self.status_var.set(f"Loaded {len(calibrations)} calibration(s)")
    
    def _get_selected_calibration(self):
        """Get the currently selected calibration name."""
        selection = self.cal_tree.selection()
        if not selection:
            return None
        item = self.cal_tree.item(selection[0])
        return item['values'][0] if item['values'] else None
    
    def _on_calibration_select(self, event):
        """Handle calibration selection."""
        cal_name = self._get_selected_calibration()
        if cal_name:
            self.status_var.set(f"Selected: {cal_name}")
    
    def _create_video_calibration(self):
        """Open dialog to create a new video calibration."""
        dialog = VideoCalibrationDialog(self.root)
        self.root.wait_window(dialog.window)
        
        if dialog.result:
            name, video_path, zoom_label, distances = dialog.result
            self.status_var.set(f"Starting calibration: {name}")
            
            # Run calibration in a way that doesn't block the GUI
            self.root.withdraw()  # Hide main window during calibration
            
            try:
                calibrator = VideoCalibrator(name, video_path, zoom_label, distances)
                success = calibrator.run()
                
                if success:
                    messagebox.showinfo("Success", f"Calibration '{name}' saved successfully!")
                else:
                    messagebox.showinfo("Cancelled", "Calibration was cancelled.")
            except Exception as e:
                messagebox.showerror("Error", f"Calibration failed: {e}")
            finally:
                self.root.deiconify()  # Show main window again
                self._refresh_calibration_list()
    
    def _create_live_calibration(self):
        """Start live camera calibration."""
        messagebox.showinfo("Live Calibration", 
                          "Live camera calibration will open in a separate window.\n\n"
                          "Click on distance markers as prompted.\n"
                          "Press ESC to finish.")
        
        self.root.withdraw()
        
        try:
            from Distance.Calibration import run_legacy_calibration
            run_legacy_calibration()
        except Exception as e:
            messagebox.showerror("Error", f"Calibration failed: {e}")
        finally:
            self.root.deiconify()
            self._refresh_calibration_list()
    
    def _test_video(self):
        """Test selected calibration with video."""
        cal_name = self._get_selected_calibration()
        if not cal_name:
            messagebox.showwarning("No Selection", "Please select a calibration first.")
            return
        
        cal = get_calibration(cal_name)
        default_video = cal.get("metadata", {}).get("source_path") if cal else None
        
        # Ask for video path
        video_path = filedialog.askopenfilename(
            title="Select Video File",
            initialfile=default_video if default_video else "",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv"),
                ("All files", "*.*")
            ]
        )
        
        if not video_path:
            if default_video and messagebox.askyesno("Use Default", 
                    f"Use default video?\n{default_video}"):
                video_path = default_video
            else:
                return
        
        self.status_var.set(f"Testing {cal_name}...")
        self.root.withdraw()
        
        try:
            run_video_test(cal_name, video_path)
        except Exception as e:
            messagebox.showerror("Error", f"Test failed: {e}")
        finally:
            self.root.deiconify()
            self._refresh_calibration_list()
    
    def _test_live(self):
        """Test selected calibration with live camera."""
        cal_name = self._get_selected_calibration()
        if not cal_name:
            messagebox.showwarning("No Selection", "Please select a calibration first.")
            return
        
        points = get_calibration_points(cal_name)
        if not points or len(points) < 2:
            messagebox.showerror("Error", "Calibration has insufficient points.")
            return
        
        self.status_var.set(f"Testing {cal_name} live...")
        self.root.withdraw()
        
        try:
            load_model(points)
            test_model_live()
        except Exception as e:
            messagebox.showerror("Error", f"Test failed: {e}")
        finally:
            self.root.deiconify()
    
    def _analyze_coverage(self):
        """Analyze detection coverage for a video."""
        cal_name = self._get_selected_calibration()
        
        cal = get_calibration(cal_name) if cal_name else None
        default_video = cal.get("metadata", {}).get("source_path") if cal else None
        
        # Ask for video path
        video_path = filedialog.askopenfilename(
            title="Select Video File for Analysis",
            initialfile=default_video if default_video else "",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv"),
                ("All files", "*.*")
            ]
        )
        
        if not video_path:
            return
        
        # Ask about overlay
        show_overlay = messagebox.askyesno("Show Overlay", 
                                           "Show live overlay during analysis?")
        
        self.status_var.set("Analyzing detection coverage...")
        self.root.withdraw()
        
        try:
            results = run_detection_coverage_analysis(
                video_path=video_path,
                calibration_name=cal_name,
                show_overlay=show_overlay,
                save_results=(cal_name is not None)
            )
            
            if results:
                msg = (f"Analysis Complete!\n\n"
                       f"Total frames: {results.get('total_frames', 'N/A')}\n"
                       f"Detected frames: {results.get('detected_frames', 'N/A')}\n"
                       f"Coverage: {results.get('percent_detected', 'N/A')}%")
                messagebox.showinfo("Detection Coverage", msg)
        except Exception as e:
            messagebox.showerror("Error", f"Analysis failed: {e}")
        finally:
            self.root.deiconify()
            self._refresh_calibration_list()
    
    def _view_details(self):
        """View details of selected calibration."""
        cal_name = self._get_selected_calibration()
        if not cal_name:
            messagebox.showwarning("No Selection", "Please select a calibration first.")
            return
        
        cal = get_calibration(cal_name)
        if not cal:
            messagebox.showerror("Error", f"Calibration '{cal_name}' not found.")
            return
        
        # Create details window
        DetailsWindow(self.root, cal_name, cal)
    
    def _view_test_results(self):
        """View test results for selected calibration."""
        cal_name = self._get_selected_calibration()
        if not cal_name:
            messagebox.showwarning("No Selection", "Please select a calibration first.")
            return
        
        results = get_test_results(cal_name)
        
        if not results:
            messagebox.showinfo("No Results", f"No test results recorded for '{cal_name}'.")
            return
        
        # Create results window
        ResultsWindow(self.root, cal_name, results)
    
    def _delete_calibration(self):
        """Delete selected calibration."""
        cal_name = self._get_selected_calibration()
        if not cal_name:
            messagebox.showwarning("No Selection", "Please select a calibration first.")
            return
        
        if messagebox.askyesno("Confirm Delete", 
                              f"Are you sure you want to delete '{cal_name}'?\n\n"
                              "This action cannot be undone."):
            if delete_calibration(cal_name):
                messagebox.showinfo("Deleted", f"Calibration '{cal_name}' deleted.")
                self._refresh_calibration_list()
            else:
                messagebox.showerror("Error", "Failed to delete calibration.")
    
    def _clear_test_results(self):
        """Clear test results for selected calibration."""
        cal_name = self._get_selected_calibration()
        if not cal_name:
            messagebox.showwarning("No Selection", "Please select a calibration first.")
            return
        
        results = get_test_results(cal_name)
        if not results:
            messagebox.showinfo("No Results", f"No test results to clear for '{cal_name}'.")
            return
        
        if messagebox.askyesno("Confirm Clear", 
                              f"Are you sure you want to delete all {len(results)} test results for '{cal_name}'?\n\n"
                              "This action cannot be undone."):
            if clear_test_results(cal_name):
                messagebox.showinfo("Cleared", f"Test results for '{cal_name}' cleared.")
                self._refresh_calibration_list()
            else:
                messagebox.showerror("Error", "Failed to clear test results.")
    
    def run(self):
        """Start the GUI event loop."""
        self.root.mainloop()


class VideoCalibrationDialog:
    """Dialog for creating a new video calibration."""
    
    def __init__(self, parent):
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("New Video Calibration")
        self.window.geometry("500x450")
        self.window.transient(parent)
        self.window.grab_set()
        
        self._create_widgets()
        
        # Center the dialog
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.window.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Create dialog widgets."""
        frame = ttk.Frame(self.window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Name
        ttk.Label(frame, text="Calibration Name:").pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.name_var, width=40).pack(fill=tk.X, pady=(0, 10))
        
        # Video path
        ttk.Label(frame, text="Video File:").pack(anchor=tk.W)
        video_frame = ttk.Frame(frame)
        video_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.video_var = tk.StringVar()
        ttk.Entry(video_frame, textvariable=self.video_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(video_frame, text="Browse...", command=self._browse_video).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Zoom label
        ttk.Label(frame, text="Zoom Label (e.g., '1x', '2x', 'wide'):").pack(anchor=tk.W)
        self.zoom_var = tk.StringVar(value="1x")
        ttk.Entry(frame, textvariable=self.zoom_var, width=20).pack(anchor=tk.W, pady=(0, 10))
        
        # Distances
        ttk.Label(frame, text="Distance Values (feet, comma-separated, increasing order):").pack(anchor=tk.W)
        ttk.Label(frame, text="Example: 10, 15, 20, 25, 30, 35, 40", 
                  font=('Helvetica', 9, 'italic')).pack(anchor=tk.W)
        self.distances_var = tk.StringVar(value="10, 15, 20, 25, 30, 35, 40, 45, 50")
        ttk.Entry(frame, textvariable=self.distances_var, width=50).pack(fill=tk.X, pady=(0, 20))
        
        # Info text
        info_text = ("Instructions:\n"
                    "1. Enter a unique name for this calibration\n"
                    "2. Select the video file to calibrate with\n"
                    "3. Set the zoom label for reference\n"
                    "4. Enter distance values you'll mark in the video\n"
                    "5. Click Start to begin - click on each distance marker in the video")
        
        info_label = ttk.Label(frame, text=info_text, justify=tk.LEFT, 
                               font=('Helvetica', 9), foreground='gray')
        info_label.pack(anchor=tk.W, pady=(0, 20))
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="Cancel", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Start Calibration", command=self._start).pack(side=tk.RIGHT)
    
    def _browse_video(self):
        """Open file browser for video selection."""
        path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv"),
                ("All files", "*.*")
            ]
        )
        if path:
            self.video_var.set(path)
    
    def _start(self):
        """Validate and start calibration."""
        name = self.name_var.get().strip()
        video_path = self.video_var.get().strip()
        zoom_label = self.zoom_var.get().strip() or "default"
        distances_str = self.distances_var.get().strip()
        
        # Validation
        if not name:
            messagebox.showerror("Error", "Please enter a calibration name.")
            return
        
        if not video_path or not os.path.isfile(video_path):
            messagebox.showerror("Error", "Please select a valid video file.")
            return
        
        # Parse distances
        try:
            distances = [float(d.strip()) for d in distances_str.split(',')]
            if len(distances) < 2:
                raise ValueError("Need at least 2 distances")
            
            # Check increasing order
            for i in range(1, len(distances)):
                if distances[i] <= distances[i-1]:
                    raise ValueError("Distances must be in increasing order")
        except Exception as e:
            messagebox.showerror("Error", f"Invalid distances: {e}")
            return
        
        self.result = (name, video_path, zoom_label, distances)
        self.window.destroy()


class DetailsWindow:
    """Window showing calibration details."""
    
    def __init__(self, parent, cal_name, cal_data):
        self.window = tk.Toplevel(parent)
        self.window.title(f"Calibration Details: {cal_name}")
        self.window.geometry("550x500")
        
        self._create_widgets(cal_name, cal_data)
    
    def _create_widgets(self, cal_name, cal):
        """Create detail widgets."""
        frame = ttk.Frame(self.window, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text=cal_name, font=('Helvetica', 14, 'bold')).pack(anchor=tk.W)
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Metadata
        metadata = cal.get("metadata", {})
        resolution = metadata.get("resolution", {})
        
        info_text = (
            f"Source Type: {metadata.get('source_type', 'unknown')}\n"
            f"Source Path: {metadata.get('source_path', 'N/A')}\n"
            f"Zoom Label: {metadata.get('zoom_label', 'unknown')}\n"
            f"Resolution: {resolution.get('width', 'N/A')}x{resolution.get('height', 'N/A')}\n"
            f"FPS: {metadata.get('fps', 'N/A')}\n"
            f"Created: {cal.get('created_at', 'unknown')}"
        )
        
        ttk.Label(frame, text="Metadata", font=('Helvetica', 11, 'bold')).pack(anchor=tk.W)
        ttk.Label(frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 10))
        
        # Calibration points
        ttk.Label(frame, text="Calibration Points", font=('Helvetica', 11, 'bold')).pack(anchor=tk.W)
        
        points_frame = ttk.Frame(frame)
        points_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ('y_pixel', 'distance')
        points_tree = ttk.Treeview(points_frame, columns=columns, show='headings', height=8)
        points_tree.heading('y_pixel', text='Y-Pixel')
        points_tree.heading('distance', text='Distance (ft)')
        points_tree.column('y_pixel', width=100)
        points_tree.column('distance', width=100)
        
        for y, dist in cal.get("calibration_points", []):
            points_tree.insert('', tk.END, values=(y, dist))
        
        points_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(points_frame, orient=tk.VERTICAL, command=points_tree.yview)
        points_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Test results summary
        results = cal.get("test_results", [])
        if results:
            avg_error = sum(abs(r.get("error_percent", 0)) for r in results) / len(results)
            test_text = f"Total tests: {len(results)}, Average error: {avg_error:.2f}%"
        else:
            test_text = "No test results recorded."
        
        ttk.Label(frame, text="Test Results", font=('Helvetica', 11, 'bold')).pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(frame, text=test_text).pack(anchor=tk.W)
        
        # Detection coverage
        coverage = cal.get("detection_coverage")
        if coverage:
            coverage_text = (f"Total frames: {coverage.get('total_frames', 'N/A')}, "
                           f"Detected: {coverage.get('detected_frames', 'N/A')}, "
                           f"Coverage: {coverage.get('percent_detected', 'N/A')}%")
        else:
            coverage_text = "No detection coverage analysis run."
        
        ttk.Label(frame, text="Detection Coverage", font=('Helvetica', 11, 'bold')).pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(frame, text=coverage_text).pack(anchor=tk.W)
        
        # Close button
        ttk.Button(frame, text="Close", command=self.window.destroy).pack(pady=(15, 0))


class ResultsWindow:
    """Window showing test results."""
    
    def __init__(self, parent, cal_name, results):
        self.window = tk.Toplevel(parent)
        self.window.title(f"Test Results: {cal_name}")
        self.window.geometry("700x450")
        
        self._create_widgets(cal_name, results)
    
    def _create_widgets(self, cal_name, results):
        """Create results widgets."""
        frame = ttk.Frame(self.window, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text=f"Test Results: {cal_name}", 
                  font=('Helvetica', 14, 'bold')).pack(anchor=tk.W)
        
        # Summary
        total_error = sum(abs(r.get("error_percent", 0)) for r in results)
        avg_error = total_error / len(results) if results else 0
        
        summary_text = f"Total test points: {len(results)} | Average absolute error: {avg_error:.2f}%"
        ttk.Label(frame, text=summary_text).pack(anchor=tk.W, pady=(5, 10))
        
        # Results table
        columns = ('num', 'known', 'estimated', 'error', 'frame', 'timestamp')
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)
        
        tree.heading('num', text='#')
        tree.heading('known', text='Known (ft)')
        tree.heading('estimated', text='Estimated (ft)')
        tree.heading('error', text='Error %')
        tree.heading('frame', text='Frame')
        tree.heading('timestamp', text='Timestamp')
        
        tree.column('num', width=40)
        tree.column('known', width=80)
        tree.column('estimated', width=100)
        tree.column('error', width=80)
        tree.column('frame', width=80)
        tree.column('timestamp', width=150)
        
        for i, r in enumerate(results, 1):
            known = r.get("known_distance", 0)
            est = r.get("estimated_distance", 0)
            error = r.get("error_percent", 0)
            frame_num = r.get("frame_number", "N/A")
            timestamp = r.get("timestamp", "N/A")[:19]
            
            tree.insert('', tk.END, values=(
                i, f"{known:.1f}", f"{est:.2f}", f"{error:.1f}%", frame_num, timestamp
            ))
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Close button
        ttk.Button(self.window, text="Close", command=self.window.destroy).pack(pady=10)


def run_gui():
    """Launch the GUI application."""
    app = CalibrationManagerGUI()
    app.run()


if __name__ == "__main__":
    run_gui()
