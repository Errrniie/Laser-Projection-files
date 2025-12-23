
from Laser.LaserEnable import Controller

from Motion.Home import home_manta
from Motion.Wait import wait_for_complete,init_ws

from Behavior.Search import SearchThread, _pan_state as search_state
from Behavior.Tracking import TrackThread, reset_tracking, _state as track_state
import time

from YoloModel.YoloInterface import show_frame, detect_human_live

FRAME_WIDTH = 640

STATE_SEARCH = "SEARCH"
STATE_TRACK  = "TRACK"

LOST_LIMIT = 8

def main():
    init_ws()
    print("Homing Manta...")
    home_manta()
    wait_for_complete() 
    print("Homing complete.  Entering SEARCH mode.")

    state = STATE_SEARCH
    lost_count = 0
    search_thread = None
    track_thread = None
    current_z = 10.0

    while True:
        loop_start = time.time()
        
        # ---- VISION ----
        human, center, bbox, conf, frame = detect_human_live()
        vision_time = time.time() - loop_start

        # ---- VISUALS ----
        if frame is not None:
            show_frame(frame, bbox, conf)

        # ---- STATE MACHINE ----
        if state == STATE_SEARCH:
            if search_thread is None:
                search_thread = SearchThread()
                search_thread.start()
            if human: 
                transition_start = time.time()
                print("Target acquired → TRACK")
                if search_thread: 
                    search_thread.stop()
                    search_thread = None
                current_z = search_state.current_z
    
                reset_tracking(z_start=current_z)
                track_thread = TrackThread(center[0], FRAME_WIDTH)
                track_thread.start()
                state = STATE_TRACK
                lost_count = 0
                transition_time = time.time() - transition_start
                print(f"  Transition took: {transition_time*1000:.1f}ms")

        elif state == STATE_TRACK:
            if not human: 
                lost_count += 1
                if lost_count >= LOST_LIMIT:  
                    print("Target lost → SEARCH")
                    if track_thread:
                        track_thread.stop()
                        track_thread = None
                    current_z = track_state. current_z
                    state = STATE_SEARCH
                    continue
            else:
                lost_count = 0
                if center is not None:
                    cx, cy = center
                    if track_thread:
                        track_thread.update_center(cx)
        
        loop_time = time.time() - loop_start
        if loop_time > 0.05:  # Print if loop takes > 50ms
            print(f"Slow loop: {loop_time*1000:.1f}ms (vision: {vision_time*1000:.1f}ms)")
            
if __name__ == "__main__":
    main()
