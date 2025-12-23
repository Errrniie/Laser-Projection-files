import threading
from Motion.Moonraker_ws import MoonrakerWSClient
from Motion.Wait import wait_for_complete
from Behavior.MotionGate import motion_lock, motion_in_flight


def wait_and_release(timeout=2.0):
    """
    Waits for the current move to complete, then clears the motion_in_flight event.
    This should be run in a background thread.
    """
    try:
        # wait_for_complete blocks until the move is done
        wait_for_complete(timeout=timeout) 
    except Exception as e:
        print(f"[MotionGate] Exception while waiting for move: {e}")
    finally:
        # This is the crucial step: signal that the motion is finished.
        motion_in_flight.clear()
        print("[MotionGate] Move complete. Gate is now open.")

def safe_move(ws_client: MoonrakerWSClient, z: float, speed: int):
    """
    A non-blocking, thread-safe function to move the Manta Z-axis.
    It respects the motion gate and is ideal for real-time tracking.
    If a move is already in flight, this function does nothing.
    """
    # If a move is already in progress, drop this correction.
    if motion_in_flight.is_set():
        return

    # Try to acquire the lock without blocking.
    if motion_lock.acquire(blocking=False):
        try:
            motion_in_flight.set()
            print(f"[MotionGate] Gate closed. Moving Z by {z:.2f}mm")
            
            ws_client.call(
                "printer.gcode.script",
                {"script": f"G91 \n G0 Z{z} F{speed * 60} \n G90"}
            )
            
            # Start a background thread to wait for completion and release the gate.
            release_thread = threading.Thread(target=wait_and_release, daemon=True)
            release_thread.start()

        except Exception as e:
            print(f"Error during safe_move: {e}")
            motion_in_flight.clear() # Clear the flag on error
        finally:
            motion_lock.release()

def safe_move_and_wait(ws_client: MoonrakerWSClient, z: float, speed: int, timeout=5.0):
    """
    A blocking, thread-safe function to move the Manta Z-axis.
    It acquires the motion lock, sends the move, waits for completion, and releases the lock.
    Ideal for sequential tasks like searching.
    """
    # Wait until the lock is available, then acquire it.
    with motion_lock:
        motion_in_flight.set()
        print(f"[MotionGate] Gate closed. Moving Z to {z} and waiting...")
        try:
            ws_client.call(
                "printer.gcode.script",
                {"script": f"G90 \n G0 Z{z} F{speed * 60}"}
            )
            # Block and wait right here.
            wait_for_complete(timeout=timeout)
        except Exception as e:
            print(f"Error during safe_move_and_wait: {e}")
        finally:
            # Release the gate so other threads can move.
            motion_in_flight.clear()
            print("[MotionGate] Move complete. Gate is now open.")
