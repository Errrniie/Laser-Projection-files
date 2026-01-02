import math
import time

from Motion.Moonraker_ws_v2 import MoonrakerWSClient

# =========================
# USER SETTINGS
# =========================

MOONRAKER_WS_URL = "ws://192.168.8.146/websocket"

CAMERA_HEIGHT_FT = 3.67
NEUTRAL_Y = 68.4          # your new neutral
SEND_FEEDRATE = 800      # tweak if your macro uses it (safe default)

# If increasing Y makes beam go UP, then down is negative delta (target < neutral).
Y_INCREASES_BEAM_UP = True

# =========================
# GEOMETRY
# =========================

def down_angle_deg(distance_ft: float, height_ft: float) -> float:
    """Down angle from horizontal needed to hit ground at distance_ft."""
    return math.degrees(math.atan2(height_ft, distance_ft))

# =========================
# MAIN
# =========================

def main():
    ws = MoonrakerWSClient(MOONRAKER_WS_URL)
    ws.connect()

    # We track commanded Y ourselves because your move path is RELATIVE.
    current_y = NEUTRAL_Y

    print("Connected.")
    print(f"Camera height: {CAMERA_HEIGHT_FT} ft")
    print(f"Neutral Y: {NEUTRAL_Y} (units: ~beam-deg)")
    print("NOTE: Sending RELATIVE Y deltas only. X untouched.")

    # Optional: move to neutral by relative delta from "wherever you are now"
    # If you want this to be deterministic, you must home first outside this script.
    # Here we just assume you're already at neutral or you manually set it.
    while True:
        try:
            dist_ft = float(input("\nDistance in feet (Ctrl+C to quit): "))
        except KeyboardInterrupt:
            break
        except ValueError:
            print("Invalid number.")
            continue

        a = down_angle_deg(dist_ft, CAMERA_HEIGHT_FT)

        # Target Y in your coordinate system
        # If Y+ moves beam UP, then to go DOWN we subtract the down-angle.
        if Y_INCREASES_BEAM_UP:
            target_y = round(NEUTRAL_Y - a, 2)
        else:
            target_y = round(NEUTRAL_Y + a, 2)

        delta_y = round(target_y - current_y, 2)  # RELATIVE command

        print(f"down_angle = {a:.3f} deg")
        print(f"target_y   = {target_y:.2f}")
        print(f"delta_y    = {delta_y:+.2f} (relative move)")

        # Send RELATIVE move using your existing "Move" style command.
        # This matches the convention used in your MotionController for relative axes.
        ws.send_gcode(f"Move y={delta_y:.2f}")

        # Update our software state
        current_y = target_y

        time.sleep(0.05)

    ws.close()
    print("Disconnected.")

if __name__ == "__main__":
    main()
