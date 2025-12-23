from Motion.Moonraker_ws import MoonrakerWSClient
from Behavior.MotionGate import motion_lock, motion_in_flight
from Motion.Move import wait_and_release

def home_manta(ws_client: MoonrakerWSClient):
    """
    Homes the Manta's axes in a thread-safe manner.
    It acquires the motion lock and sets the in-flight event.
    """
    # First, wait for any existing move to finish and for the lock to be free
    if motion_in_flight.is_set():
        wait_and_release() # Clear the previous move if it's stuck

    with motion_lock:
        motion_in_flight.set()
        try:
            print("Sending G28 (Home) command...")
            ws_client.call(
                "printer.gcode.script",
                {"script": "G28"},
            )
        except Exception:
            # A timeout is expected here as the command takes a long time
            # and the library doesn't wait for completion.
            pass 
        
        # We must now wait for the homing to complete before releasing the gate
        print("Waiting for homing to complete...")
        wait_and_release(timeout=20.0) # Use a long timeout for homing
        print("Homing complete, motion gate released.")
