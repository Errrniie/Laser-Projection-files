from Laser.LaserEnable import Controller

from Motion.Home import home_manta
from Motion.Wait import wait_for_complete,init_ws

from Behavior.Search import SearchThread
from Behavior.Tracking import TrackThread, reset_tracking
import time

from YoloModel.YoloInterface import show_frame, detect_human_live

FRAME_WIDTH = 640

STATE_SEARCH = "SEARCH"
STATE_TRACK  = "TRACK"

LOST_LIMIT = 8

def main():
    init_ws()
    laser = Controller()

    print("Homing Manta...")
    home_manta()
    wait_for_complete() 
    print("Homing complete. Entering SEARCH mode.")

    state = STATE_SEARCH
    lost_count = 0
    search_thread = None
    track_thread = None

    while True:
        # ---- VISION ----
        human, center, bbox, conf, frame = detect_human_live()

        # ---- VISUALS ----
        if frame is not None:
            show_frame(frame, bbox, conf)

        # ---- STATE MACHINE ----
        if state == STATE_SEARCH:
            if human:
                print("Target acquired → TRACK")
                if search_thread:
                    search_thread.stop()
                    search_thread.join()
                    search_thread = None
                reset_tracking()
                track_thread = TrackThread(center[0], FRAME_WIDTH)
                track_thread.start()
                state = STATE_TRACK
                lost_count = 0
            else:
                if not search_thread or not search_thread.is_alive():
                    search_thread = SearchThread()
                    search_thread.start()

        elif state == STATE_TRACK:
            if not human:
                lost_count += 1
                if lost_count >= LOST_LIMIT:
                    print("Target lost → SEARCH")
                    if track_thread:
                        track_thread.stop()
                        track_thread.join()
                        track_thread = None
                    state = STATE_SEARCH
                continue

            lost_count = 0
            cx, cy = center
            if track_thread:
                track_thread.update_center(cx)


if __name__ == "__main__":
    main()
