
import time
from YoloModel.Detection import detect_human
from YoloModel.CameraThread import CameraThread
import cv2
import threading
import queue

# --- Globals ---
camera = None
_display_thread = None
_vision_thread = None
_display_queue = queue.Queue(maxsize=1)
_vision_queue = queue.Queue(maxsize=1)

# --- Stop Events ---
_stop_event = threading.Event()

# --- Constants ---
_WINDOW_NAME = "Goose Vision"
_VISION_LOOP_INTERVAL = 0.05  # Process frames at 10Hz

def start_vision():
    """Initializes and starts all vision-related threads."""
    global camera, _display_thread, _vision_thread
    print("Vision system starting...")

    if camera is None:
        camera = CameraThread(index=4, width=640, height=480, fps=30)
    
    _stop_event.clear()
    
    # Start all threads
    camera.start()
    
    _vision_thread = threading.Thread(target=_vision_worker, daemon=True)
    _vision_thread.start()

    _display_thread = threading.Thread(target=_display_worker, daemon=True)
    _display_thread.start()
    
    print("Vision system started.")

def stop_vision():
    """Stops all vision-related threads and releases resources."""
    global camera, _display_thread, _vision_thread
    print("Vision system stopping...")
    
    _stop_event.set()

    if camera:
        camera.stop()
        camera = None

    if _vision_thread and _vision_thread.is_alive():
        _vision_thread.join()
        _vision_thread = None
        
    if _display_thread and _display_thread.is_alive():
        _display_thread.join()
        _display_thread = None

    cv2.destroyAllWindows()
    print("Vision system stopped.")

def _vision_worker():
    """
    Dedicated thread for running object detection at a controlled rate.
    """
    while not _stop_event.is_set():
        loop_start_time = time.time()

        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue
        
        # --- This is the expensive operation ---
        human, center, bbox, conf = detect_human(frame)
        
        try:
            # Put the full results packet into the queue
            _vision_queue.put_nowait((human, center, bbox, conf, frame))
        except queue.Full:
            pass # Discard if the main loop is not keeping up

        # --- Rate-limit the loop to free up CPU ---
        elapsed_time = time.time() - loop_start_time
        sleep_time = _VISION_LOOP_INTERVAL - elapsed_time
        if sleep_time > 0:
            time.sleep(sleep_time)

def _display_worker():
    """Separate thread handles all visualization"""
    while not _stop_event.is_set():
        try:
            frame, bbox, conf = _display_queue.get(timeout=0.1)
            vis = frame.copy()

            if bbox is not None:
                x1, y1, x2, y2 = bbox
                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    vis, f"{conf:.2f}", (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1
                )

            h, w = vis.shape[:2]
            cv2.drawMarker(
                vis, (w // 2, h // 2),
                (255, 0, 0), cv2.MARKER_CROSS, 20, 2
            )

            cv2.imshow(_WINDOW_NAME, vis)
            cv2.waitKey(1)
        except queue.Empty:
            if _stop_event.is_set():
                break

def detect_human_live():
    """Non-blocking call to get the latest detection result."""
    try:
        return _vision_queue.get_nowait()
    except queue.Empty:
        return False, None, None, 0.0, None

def show_frame(frame, bbox=None, conf=None):
    """Non-blocking frame display."""
    try:
        _display_queue.put_nowait((frame, bbox, conf))
    except queue.Full:
        pass
