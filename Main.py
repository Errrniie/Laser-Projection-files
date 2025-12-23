
from Motion.Home import home_manta
from Motion.Wait import wait_for_complete, init_ws
from Motion.Move import Move
from Motion.Position import get_motor_positions
from Motion.Moonraker_ws import MoonrakerWSClient

from Behavior.Search import SearchThread
from Behavior.Tracking import TrackThread, reset_tracking
from Behavior.UserInput import UserInputThread, should_quit

import time

from YoloModel.YoloInterface import show_frame, detect_human_live, start_vision, stop_vision

MOONRAKER_HOST = "192.168.8.146"
WS_URL = f"ws://{MOONRAKER_HOST}/websocket" 
FRAME_WIDTH = 640
STATE_SEARCH = "SEARCH"
STATE_TRACK = "TRACK"
LOST_LIMIT = 30
SEARCH_SPEED = 400

ws_client = MoonrakerWSClient(WS_URL)
ws_client.connect()

def main():
    init_ws()
    print("Homing Manta...")
    home_manta()
    wait_for_complete()
    print("Homing complete. Entering SEARCH mode.")

    start_vision()
    
    user_input_thread = UserInputThread()
    user_input_thread.start()

    state = STATE_SEARCH
    lost_count = 0
    search_thread = None
    track_thread = None
    last_lost_time = 0

    try:
        while not should_quit():
            human, center, bbox, conf, frame = detect_human_live()

            if frame is not None:
                show_frame(frame, bbox, conf)

            if state == STATE_SEARCH:
                if search_thread is None and not should_quit():
                    search_thread = SearchThread()
                    search_thread.start()
                
                if time.time() - last_lost_time < 2.0:
                    continue

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

            elif state == STATE_TRACK:
                if not human:
                    lost_count += 1
                    if lost_count >= LOST_LIMIT:
                        print("Target lost → SEARCH")
                        last_lost_time = time.time()
                        if track_thread:
                            track_thread.stop()
                            track_thread.join()
                            track_thread = None
                        
                        try:
                            pos = get_motor_positions()
                            if pos and 'z' in pos:
                                current_z = float(pos['z'])
                                rounded_z = round(current_z)
                                diff_z = rounded_z - current_z
                                
                                if abs(diff_z) > 0.001:
                                    print(f"Snapping to grid: {current_z:.3f} -> {rounded_z}. Moving by {diff_z:.3f}")
                                    Move(z=diff_z, speed=SEARCH_SPEED)
                                    wait_for_complete()
                        except Exception as e:
                            print(f"Error during grid snapping: {e}")
                        
                        state = STATE_SEARCH
                        continue
                else:
                    lost_count = 0
                    if center is not None and track_thread is not None:
                        track_thread.update_center(center[0])
            
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("Program interrupted by user.")
    finally:
        print("Shutdown requested...")
        # Signal all threads to stop
        if user_input_thread:
            user_input_thread.stop()
        if search_thread:
            search_thread.stop()
        if track_thread:
            track_thread.stop()
        stop_vision()
        
        # Wait for threads to finish
        if user_input_thread and user_input_thread.is_alive():
            user_input_thread.join()
        if search_thread and search_thread.is_alive():
            search_thread.join()
        if track_thread and track_thread.is_alive():
            track_thread.join()

        # Final safety move: return Z to 0
        try:
            print("Returning Z to home position...")
            pos = get_motor_positions()
            if pos and 'z' in pos:
                current_z = float(pos['z'])
                Move(z=-current_z, speed=1000) # Move at a good speed
                wait_for_complete()
            print("Z axis homed.")
        except Exception as e:
            print(f"Could not home Z axis: {e}")
        
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
