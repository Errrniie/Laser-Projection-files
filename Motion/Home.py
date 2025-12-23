from Motion.Moonraker_ws import MoonrakerWSClient
from Behavior.MotionGate import motion_lock, motion_in_flight

def home_manta(ws_client: MoonrakerWSClient):
    """
    Homes the Manta's axes in a blocking, thread-safe manner.
    This function will wait until homing is fully complete before returning.
    """
    # Acquire the motion lock, waiting if necessary. This ensures no other
    # motion commands can be sent while homing.
    with motion_lock:
        motion_in_flight.set() # Signal that a critical motion is in progress
        try:
            print("Sending G28 (Home) command and waiting for completion...")
            # Use a long timeout because homing can take a while.
            # The ws_client.call will block until the command is acknowledged
            # by Moonraker as complete.
            ws_client.call(
                "printer.gcode.script",
                {"script": "G28"},
                timeout_s=30.0 # 30-second timeout for homing
            )
            print("Homing complete.")
        except Exception as e:
            print(f"An error occurred during homing: {e}")
            # Re-raise the exception to signal failure to the caller
            raise
        finally:
            # Ensure the motion flag is cleared, opening the gate for other moves.
            motion_in_flight.clear()
            print("Motion gate released after homing.")
