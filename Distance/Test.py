# Distance/Test.py
"""
Test module for distance estimation.
Supports both video and live camera testing with test point recording.
"""

import time
import sys
import os

# Adjust the Python path to include the root directory of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Distance.VideoHandler import VideoHandler, draw_video_controls, handle_video_key, resize_for_display
from Distance.Model import load_model, get_distance
from Distance.Storage import (
    get_calibration, get_calibration_points, add_test_result, get_test_results
)
from YoloModel.Detection import detect_human


class VideoTester:
    """
    Handles video-based testing of a calibration.
    Runs YOLO, overlays feet marker and distance, allows recording test points.
    """

    def __init__(self, calibration_name, video_path=None):
        """
        Initialize the tester.
        
        Args:
            calibration_name: Name of the calibration to test
            video_path: Path to video file (if None, uses calibration's source video)
        """
        self.calibration_name = calibration_name
        self.calibration = get_calibration(calibration_name)
        
        if self.calibration is None:
            raise ValueError(f"Calibration '{calibration_name}' not found.")
        
        # Load the model
        points = get_calibration_points(calibration_name)
        if not points or len(points) < 2:
            raise ValueError("Calibration has insufficient points.")
        load_model(points)
        
        # Determine video path
        if video_path:
            self.video_path = video_path
        else:
            self.video_path = self.calibration.get("metadata", {}).get("source_path")
        
        if not self.video_path or not os.path.isfile(self.video_path):
            raise ValueError(f"Video file not found: {self.video_path}")
        
        self.video = None
        self.last_detection = None
        self.test_session_results = []
    
    def _get_feet_center(self, bbox):
        """Calculate feet center from bounding box (bottom-center)."""
        if bbox is None:
            return None
        x1, y1, x2, y2 = bbox
        return (int((x1 + x2) / 2), y2)
    
    def _draw_test_overlay(self, frame, scale=1.0):
        """Draw test-specific overlay on frame (scaled for display)."""
        h, w = frame.shape[:2]
        
        if self.last_detection:
            human, center, bbox, conf, feet_center = self.last_detection
            
            if bbox is not None:
                x1, y1, x2, y2 = bbox
                # Scale bbox coordinates
                x1_s, y1_s = int(x1 * scale), int(y1 * scale)
                x2_s, y2_s = int(x2 * scale), int(y2 * scale)
                cv2.rectangle(frame, (x1_s, y1_s), (x2_s, y2_s), (0, 255, 0), 2)
            
            if feet_center is not None:
                # Scale feet center for display
                feet_scaled = (int(feet_center[0] * scale), int(feet_center[1] * scale))
                
                # Draw feet marker
                cv2.drawMarker(frame, feet_scaled, (0, 0, 255), cv2.MARKER_STAR, 15, 2)
                
                # Get and display estimated distance
                estimated_dist = get_distance(feet_center[1])
                
                # Draw distance info box (fixed position at bottom)
                info_x, info_y = 10, h - 85
                cv2.rectangle(frame, (info_x, info_y), (info_x + 220, info_y + 45), (0, 0, 0), -1)
                cv2.rectangle(frame, (info_x, info_y), (info_x + 220, info_y + 45), (255, 255, 255), 1)
                
                cv2.putText(frame, f"Feet Y: {feet_center[1]}", 
                           (info_x + 8, info_y + 18),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(frame, f"Est. Distance: {estimated_dist:.2f} ft", 
                           (info_x + 8, info_y + 38),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        
        # Draw calibration info
        zoom = self.calibration.get("metadata", {}).get("zoom_label", "unknown")
        cv2.putText(frame, f"Cal: {self.calibration_name} (Zoom: {zoom})", 
                   (10, h - 95), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
        
        # Draw test session stats
        if self.test_session_results:
            avg_error = sum(r["error_percent"] for r in self.test_session_results) / len(self.test_session_results)
            stats_text = f"Session: {len(self.test_session_results)} pts, Avg Err: {abs(avg_error):.1f}%"
            cv2.putText(frame, stats_text, (w - 280, h - 95), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)
        
        return frame
    
    def _create_extra_text(self):
        """Create extra text lines for the overlay."""
        lines = []
        lines.append("[R] Record test point  [T] Show all results")
        
        if self.last_detection and self.last_detection[0]:
            lines.append(f"Human detected (conf: {self.last_detection[3]:.2f})")
        else:
            lines.append("No human detected")
        
        return lines
    
    def _prompt_known_distance(self):
        """Prompt user for known distance (uses console input while paused)."""
        print("\n" + "-"*40)
        print("RECORD TEST POINT")
        print("-"*40)
        
        try:
            dist_str = input("Enter known distance (feet): ").strip()
            known_dist = float(dist_str)
            return known_dist
        except ValueError:
            print("Invalid distance. Cancelled.")
            return None
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None
    
    def _record_test_point(self):
        """Record a test point with the current detection."""
        if not self.last_detection or not self.last_detection[0]:
            print("No human detected. Cannot record test point.")
            return
        
        feet_center = self.last_detection[4]
        if feet_center is None:
            print("Could not determine feet position.")
            return
        
        # Pause video for input
        was_paused = self.video.is_paused
        self.video.is_paused = True
        
        known_dist = self._prompt_known_distance()
        
        if known_dist is not None:
            estimated_dist = get_distance(feet_center[1])
            error_percent = ((estimated_dist - known_dist) / known_dist) * 100 if known_dist != 0 else 0
            
            test_result = {
                "known_distance": known_dist,
                "estimated_distance": round(estimated_dist, 2),
                "error_percent": round(error_percent, 2),
                "feet_y": feet_center[1],
                "frame_number": self.video.frame_number
            }
            
            # Save to storage
            add_test_result(self.calibration_name, test_result)
            
            # Add to session results
            self.test_session_results.append(test_result)
            
            print(f"Recorded: Known={known_dist}ft, Est={estimated_dist:.2f}ft, Error={error_percent:.1f}%")
        
        # Restore pause state
        self.video.is_paused = was_paused
    
    def _show_all_results(self):
        """Display all test results for this calibration."""
        results = get_test_results(self.calibration_name)
        
        print("\n" + "="*60)
        print(f"TEST RESULTS FOR: {self.calibration_name}")
        print("="*60)
        
        if not results:
            print("No test results recorded.")
            print("="*60)
            return
        
        print(f"{'Known':>10} {'Estimated':>12} {'Error':>10} {'Frame':>8}")
        print("-"*42)
        
        total_error = 0
        for r in results:
            known = r.get("known_distance", 0)
            est = r.get("estimated_distance", 0)
            error = r.get("error_percent", 0)
            frame = r.get("frame_number", "N/A")
            
            print(f"{known:>10.1f} {est:>12.2f} {error:>9.1f}% {frame:>8}")
            total_error += abs(error)
        
        avg_error = total_error / len(results)
        print("-"*42)
        print(f"Average absolute error: {avg_error:.2f}%")
        print(f"Total test points: {len(results)}")
        print("="*60 + "\n")
    
    def run(self):
        """Run the test session."""
        self.video = VideoHandler(self.video_path)
        
        if not self.video.open():
            return False
        
        window_name = f"Test: {self.calibration_name}"
        cv2.namedWindow(window_name)
        
        print("\n" + "="*60)
        print("VIDEO TEST MODE")
        print("="*60)
        print("Controls:")
        print("  [SPACE] - Play/Pause video")
        print("  [<] [>] or [,] [.] - Step frame backward/forward")
        print("  [R] - Record test point (prompts for known distance)")
        print("  [T] - Show all test results")
        print("  [Q] or [ESC] - Quit")
        print("="*60 + "\n")
        
        try:
            while True:
                frame = self.video.get_frame()
                if frame is None:
                    break
                
                # Run detection on current frame (original resolution)
                human, center, bbox, conf = detect_human(frame)
                feet_center = self._get_feet_center(bbox)
                self.last_detection = (human, center, bbox, conf, feet_center)
                
                # Resize for display FIRST, then draw overlays for crisp text
                vis_resized, scale = resize_for_display(frame.copy(), max_width=1280, max_height=720)
                
                # Draw overlays on resized frame
                vis_resized = self._draw_test_overlay(vis_resized, scale=scale)
                extra_text = self._create_extra_text()
                vis_resized = draw_video_controls(vis_resized, self.video, extra_text)
                
                cv2.imshow(window_name, vis_resized)
                
                key = cv2.waitKey(30) & 0xFF
                
                # Handle video controls
                should_quit, action = handle_video_key(key, self.video)
                if should_quit:
                    break
                
                # Handle test-specific keys
                if key == ord('r') or key == ord('R'):
                    self._record_test_point()
                
                elif key == ord('t') or key == ord('T'):
                    self._show_all_results()
        
        finally:
            self.video.close()
            cv2.destroyAllWindows()
            
            # Show final summary
            if self.test_session_results:
                print(f"\nSession complete. Recorded {len(self.test_session_results)} test points.")
                self._show_all_results()
        
        return True


def run_video_test(calibration_name, video_path=None):
    """
    Run a video test session.
    
    Args:
        calibration_name: Name of the calibration to test
        video_path: Optional video path (uses calibration's source if not provided)
    """
    try:
        tester = VideoTester(calibration_name, video_path)
        return tester.run()
    except ValueError as e:
        print(f"Error: {e}")
        return False


# Import cv2 here to avoid issues with the module import in VideoTester
import cv2


# --- Legacy functions for backward compatibility ---

def test_model_live():
    """
    Legacy function: Tests the loaded distance model with live camera.
    Kept for backward compatibility.
    """
    from Distance.YoloInterface import start_vision, stop_vision, detect_human_live
    
    print("\nStarting live distance estimation test...")
    start_vision()

    try:
        while True:
            human, _, bbox, _, frame, feet_center = detect_human_live()

            if frame is not None:
                vis = frame.copy()
                
                if bbox:
                    x1, y1, x2, y2 = bbox
                    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                if human and feet_center:
                    estimated_distance = get_distance(feet_center[1])
                    cv2.drawMarker(vis, feet_center, (0, 0, 255), cv2.MARKER_STAR, 20, 2)
                    cv2.putText(vis, f"Est: {estimated_distance:.2f} ft", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                cv2.imshow("Live Test", vis)
            
            key = cv2.waitKey(1) & 0xFF
            if key in [ord('q'), 27]:
                break
            
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("Test interrupted by user.")
    finally:
        stop_vision()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    from Distance.Storage import list_calibrations, load_calibration_data
    
    calibrations = list_calibrations()
    
    if not calibrations:
        print("No calibrations found. Please run calibration first.")
        sys.exit(1)
    
    print("\nAvailable calibrations:")
    for i, cal in enumerate(calibrations, 1):
        print(f"  {i}. {cal['name']} (Zoom: {cal['zoom_label']}, Points: {cal['num_points']})")
    
    try:
        choice = int(input("\nSelect calibration number: ").strip()) - 1
        if 0 <= choice < len(calibrations):
            cal_name = calibrations[choice]["name"]
            
            # Ask for video path or use default
            video_input = input("Enter video path (or press Enter to use calibration source): ").strip()
            video_path = video_input if video_input else None
            
            run_video_test(cal_name, video_path)
        else:
            print("Invalid selection.")
    except (ValueError, KeyboardInterrupt):
        print("\nExiting.")
