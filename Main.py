from Motion.Moonraker_ws_v2 import MoonrakerWSClient
from Motion.MotionController import MotionController
from Motion.Home import home
from Behavior.Search_v2 import SearchController, SearchConfig
import Config.Seach_Config as search_config

# --- System states ---
STATE_INIT = "INIT"
STATE_SEARCH = "SEARCH"
STATE_SHUTDOWN = "SHUTDOWN"


def main():
    state = STATE_INIT

    moonraker = MoonrakerWSClient("ws://192.168.8.146/websocket")
    motion_cfg = {
        "limits": {"x": [-100, 100], "y": [-100, 100], "z": [0, 20]},
        "neutral": {"x": 0.0, "y": 0.0, "z": 10.0},
        "speeds": {"travel": 5000, "z": 1500},
    }
    motion = MotionController(moonraker, motion_cfg)
    
    search = SearchController(
        SearchConfig(
            min_z=search_config.min_z,
            max_z=search_config.max_z,
            start_z=search_config.start_z,
            step=search_config.step,
        )
    )
    while True:
        if state == STATE_INIT:
            print("[STATE] INIT")
            moonraker.connect()
            home(moonraker)
            motion.set_neutral_intent()
            motion.move_blocking()
            print("Initialization complete. Transitioning to SEARCH state.")
            state = STATE_SEARCH
            continue

        if state == STATE_SEARCH:
            print("[STATE] SEARCH")
            intent = search.update()
            if intent is not None:
                motion.set_intent(**intent)
            motion.update()
            import time
            time.sleep(0.01)
            continue

        if state == STATE_SHUTDOWN:
            print("[STATE] SHUTDOWN")
            motion.set_neutral_intent(z=0.0)
            motion.move_blocking()
            moonraker.close()
            break

if __name__ == "__main__":
    main()