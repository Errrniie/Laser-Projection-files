# Main.py - Refactored: Explicit Control Ownership and State Machine

from Motion.MotionController import MotionController
from Motion.Moonraker_ws_v2 import MoonrakerWSClient
from Behavior.Search_v2 import SearchController

from YoloModel.YoloInterface import (
    show_frame, detect_human_live, start_vision, stop_vision
)

import time

# --- States ---
STATE_INIT = "INIT"
STATE_SEARCH = "SEARCH"
STATE_TRACK = "TRACK"
STATE_SHUTDOWN = "SHUTDOWN"



MOONRAKER_HOST = "192.168.8.146"
WS_URL = f"ws://{MOONRAKER_HOST}/websocket" 

motion = MotionController(moon, motion_config)
search = SearchController(search_config)

state = INIT

def main():
    ws_client = None
    state = STATE_INIT
    current_z = SEARCH_START_Z
    scan_direction = 1  # 1 for up, -1 for down

    lost_count = 0
    last_human_bbox = None

    try:
        # Main handles all state and owns hardware resources
        ws_client = MoonrakerWSClient(WS_URL)
        ws_client.connect()

        running = True

        while running:
            if state == STATE_INIT:
                print("[STATE] INIT - Homing and startup sequence")
                motion.home()
                motion.set_neutral_intent()
                motion.emit_motion_blocking()
                
                search.reset()
                state = STATE_SEARCH
                print("[STATE] Transition to SEARCH")
                continue

            if state == STATE_SEARCH:
                # Compute and issue non-blocking scan Z intent
                set_motion_intent(ws_client, z=current_z)
                # Query YOLO (non-blocking)
                human, center, bbox, conf, frame = detect_human_live()
                if frame is not None:
                    show_frame(frame, bbox, conf)
                laser_off()

                if human and bbox is not None:
                    print("[SEARCH] Human detected, transitioning to TRACK")
                    last_human_bbox = bbox
                    state = STATE_TRACK
                    laser_on()
                    lost_count = 0
                    continue

                # Oscillate Z for next step
                current_z, scan_direction = compute_next_search_position(
                    current_z, scan_direction, SEARCH_LOWER_Z, SEARCH_UPPER_Z, SEARCH_STEP_Z
                )

                # Main loop timing: Small sleep to avoid CPU spin
                time.sleep(0.025)
                continue

            if state == STATE_TRACK:
                # Query YOLO (non-blocking)
                human, center, bbox, conf, frame = detect_human_live()
                if frame is not None:
                    show_frame(frame, bbox, conf)

                if human and bbox is not None:
                    # Extract feet (bottom-center of bbox)
                    x1, y1, x2, y2 = bbox
                    feet_px = ((x1 + x2) // 2, y2)
                    # In production: use calibration map to convert feet_px to ground point
                    mirror_angles = compute_mirror_angles(feet_px)
                    set_motion_intent(ws_client, mirror_angles=mirror_angles)
                    laser_on()
                    lost_count = 0
                else:
                    laser_off()
                    lost_count += 1
                    if lost_count > LOSS_LIMIT:
                        print("[TRACK] Target lost, returning to SEARCH (mirrors to neutral)")
                        # Return mirrors to neutral/SEARCH
                        set_motion_intent(ws_client, z=SEARCH_START_Z)
                        state = STATE_SEARCH
                        scan_direction = 1
                        current_z = SEARCH_START_Z
                        continue

                time.sleep(0.025)
                continue

            if state == STATE_SHUTDOWN:
                print("[STATE] SHUTDOWN: stopping hardware")
                laser_off()
                stop_vision()
                set_motion_intent(ws_client, z=0)  # Move Z to home (blocking allowed if desired)
                # Optionally: block here on motion completion if API supports it
                if ws_client and ws_client.is_connected():
                    ws_client.close()
                print("[STATE] Shutdown complete")
                running = False
                continue

            # Shutdown signal check (can insert keyboard or remote signal here)
            # For demo: Ctrl+C sets SHUTDOWN
            # Could also check for quit.txt if needed
            # Break condition:
            # if should_quit(): state = STATE_SHUTDOWN

    except (KeyboardInterrupt, Exception) as e:
        print(f"[EXCEPTION] {e}")
        state = STATE_SHUTDOWN

    finally:
        # Emergency shutoff path
        laser_off()
        try:
            stop_vision()
        except Exception:
            pass
        try:
            set_motion_intent(ws_client, z=0)
        except Exception:
            pass
        if ws_client and ws_client.is_connected():
            ws_client.close()
        print("[STATE] Final shutdown complete")

if __name__ == "__main__":
    main()