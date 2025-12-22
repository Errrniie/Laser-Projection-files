from Laser.LaserEnable import Controller
from YoloModel.yolov8 import detect_human_live

from Motion.Home import home_manta, wait_for_complete
from Manta.MantaMovement.Search import pan_z, get_current_z
from Manta.MantaMovement.Tracking import track_z, set_current_z

import time


FRAME_WIDTH = 1280

laser = Controller()

print("Homing Manta...")
home_manta()
wait_for_complete()

print("Homing complete. Entering SEARCH mode.")

STATE_SEARCH = "SEARCH"
STATE_TRACK  = "TRACK"

state = STATE_SEARCH
lost_count = 0
LOST_LIMIT = 8


while True:
    human, center, bbox, conf = detect_human_live()

    if state == STATE_SEARCH:
        laser.set_laser(False)

        if human:
            print("Human detected → TRACK")
            z_now = get_current_z()
            set_current_z(z_now)   # transfer Z ownership
            state = STATE_TRACK
            lost_count = 0
        else:
            pan_z()

    elif state == STATE_TRACK:
        laser.set_laser(False)

        if human:
            cx, cy = center
            track_z(cx, FRAME_WIDTH)
            lost_count = 0
        else:
            lost_count += 1
            if lost_count > LOST_LIMIT:
                print("Human lost → SEARCH")
                state = STATE_SEARCH

    time.sleep(0.03)
