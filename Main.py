from Laser.LaserEnable import Controller

from Motion.Home import home_manta
from Motion.Wait import wait_for_complete,init_ws

from Behavior.Search import pan_z
from Behavior.Tracking import reset_tracking, track
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

    while True:
         # ---- VISION ----
        human, center, bbox, conf, frame = detect_human_live()

        if state == STATE_SEARCH and frame is not None:
            show_frame(frame, bbox, conf)

        # ---- STATE MACHINE ----
        if state == STATE_SEARCH:
            if human:
                print("Target acquired → TRACK")
                reset_tracking()
                state = STATE_TRACK
                lost_count = 0
            else:
                pan_z()   # continuous search motion

        elif state == STATE_TRACK:
            if not human:
                lost_count += 1
                if lost_count >= LOST_LIMIT:
                    print("Target lost → SEARCH")
                    state = STATE_SEARCH
                continue

            lost_count = 0
            cx, cy = center
            track(cx, FRAME_WIDTH)


if __name__ == "__main__":
    main()