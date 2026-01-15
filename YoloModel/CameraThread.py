import cv2
import threading
import time
from Config.vision_config import get_camera_config

# Load configuration
_camera_config = get_camera_config()

class CameraThread:
    def __init__(self, index=None, width=None, height=None, fps=None):
        # Use configuration defaults if not specified
        index = index if index is not None else _camera_config.camera_index
        width = width if width is not None else _camera_config.width  
        height = height if height is not None else _camera_config.height
        fps = fps if fps is not None else _camera_config.fps
        
        # Initialize camera with configuration
        self.cap = cv2.VideoCapture(index, _camera_config.backend)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*_camera_config.fourcc))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, _camera_config.buffer_size)

        self._lock = threading.Lock()
        self._frame = None
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True
        )
        self._thread.start()

    def _loop(self):
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.005)
                continue
            with self._lock:
                self._frame = frame

    def get_frame(self):
        with self._lock:
            return self._frame

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        self.cap.release()
