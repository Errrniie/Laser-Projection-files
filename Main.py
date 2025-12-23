
from Motion.Home import home_manta
from Motion.Move import safe_move_and_wait
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

def main():
    ws_client = None
    user_input_thread = None
    search_thread = None
    track_thread = None

    try:
        ws_client = MoonrakerWSClient(WS_URL)
        ws_client.connect()

        print("Homing Manta...")
        # The new home_manta function is now blocking, so we don't need to wait separately.
        home_manta(ws_client)
        print("Homing complete. Entering SEARCH mode.")

        start_vision()
        
        user_input_thread = UserInputThread()
        user_input_thread.start()

        state = STATE_SEARCH
        lost_count = 0
        last_lost_time = 0

        while not should_quit():
            human, center, bbox, conf, frame = detect_human_live()

            if frame is not None:
                show_frame(frame, bbox, conf)

            if state == STATE_SEARCH:
                if search_thread is None and not should_quit():
                    search_thread = SearchThread(ws_client)
                    search_thread.start()
                
                if time.time() - last_lost_time < 2.0:
                    continue

                if human:
                    print("Target acquired -> TRACK")
                    if search_thread:
                        search_thread.stop()
                        search_thread = None
                    
                    reset_tracking()
                    track_thread = TrackThread(center[0], FRAME_WIDTH, ws_client)
                    track_thread.start()
                    state = STATE_TRACK
                    lost_count = 0

            elif state == STATE_TRACK:
                if not human:
                    lost_count += 1
                    if lost_count >= LOST_LIMIT:
                        print("Target lost -> SEARCH")
                        last_lost_time = time.time()
                        if track_thread:
                            track_thread.stop()
                            track_thread = None
                        
                        # The "grid snapping" logic is no longer needed with the new search behavior
                        # which moves to absolute positions.
                        
                        state = STATE_SEARCH
                        continue
                else:
                    lost_count = 0
                    if center is not None and track_thread is not None:
                        track_thread.update_center(center[0])
            
            time.sleep(0.01)

    except (KeyboardInterrupt, Exception) as e:
        print(f"An error occurred: {e}")

    finally:
        print("Shutdown requested...")
        if user_input_thread:
            user_input_thread.stop()
        if search_thread:
            search_thread.stop()
        if track_thread:
            track_thread.stop()
        
        stop_vision()
        
        # Wait for all threads to finish
        if user_input_thread and user_input_thread.is_alive():
            user_input_thread.join()
        if search_thread and search_thread.is_alive():
            search_thread.join()
        if track_thread and track_thread.is_alive():
            track_thread.join()

        if ws_client and ws_client.is_connected():
            try:
                print("Returning Z to home position...")
                # Use the new safe, blocking move to go to Z=0
                safe_move_and_wait(ws_client, z=0, speed=1000)
                print("Z axis homed.")
            except Exception as e:
                print(f"Could not home Z axis: {e}")
            finally:
                ws_client.close()

        print("Shutdown complete.")

if __name__ == "__main__":
    main()
