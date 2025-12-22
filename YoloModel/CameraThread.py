import cv2
import threading
import time

class CameraThread:
    def __init__(self, index=0, width=640, height=480, fps=30):
        self.cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

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
