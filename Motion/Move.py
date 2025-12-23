import threading
from Motion.Moonraker_ws import MoonrakerWSClient
from Motion.Wait import wait_for_complete
from Behavior.MotionGate import motion_lock, motion_in_flight

def wait_and_release(ws_client: MoonrakerWSClient, timeout=2.0):
    """
    Waits for the current move to complete, then clears the motion_in_flight event.
    This should be run in a background thread.
    """
    try:
        wait_for_complete(ws_client, timeout_s=timeout)
    except Exception as e:
        print(f"[MotionGate] Exception while waiting for move: {e}")
    finally:
        motion_in_flight.clear()
        print("[MotionGate] Move complete. Gate is now open.")

def safe_move(ws_client: MoonrakerWSClient, z: float, speed: int):
    """
    A non-blocking, thread-safe function to move the Manta Z-axis.
    It respects the motion gate and is ideal for real-time tracking.
    """
    if motion_in_flight.is_set():
        return

    if motion_lock.acquire(blocking=False):
        try:
            motion_in_flight.set()
            print(f"[MotionGate] Gate closed. Moving Z by {z:.2f}mm")
            
            ws_client.call(
                "printer.gcode.script",
                {"script": f"G91 \n G0 Z{z} F{speed * 60} \n G90"}
            )
            
            release_thread = threading.Thread(target=wait_and_release, args=(ws_client,), daemon=True)
            release_thread.start()
        except Exception as e:
            print(f"Error during safe_move: {e}")
            motion_in_flight.clear()
        finally:
            motion_lock.release()

def safe_move_and_wait(ws_client: MoonrakerWSClient, z: float, speed: int, timeout=15.0):
    """
    A blocking, thread-safe function to move the Manta Z-axis that raises
    exceptions on failure.
    """
    with motion_lock:
        motion_in_flight.set()
        print(f"[MotionGate] Gate closed. Moving Z to {z} and waiting...")
        try:
            ws_client.call(
                "printer.gcode.script",
                {"script": f"G90 \n G0 Z{z} F{speed * 60}"}
            )
            wait_for_complete(ws_client, timeout_s=timeout)
            print("[MotionGate] Move complete. Gate is now open.")
        except Exception as e:
            print(f"Error during safe_move_and_wait: {e}")
            # Re-raise the exception to be handled by the caller
            raise
        finally:
            motion_in_flight.clear()
