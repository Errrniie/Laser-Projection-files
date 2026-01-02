"""
Motion Latency Test Script
Measures round-trip latency for MOVE commands via Moonraker WebSocket.
"""

from Motion.Moonraker_ws_v2 import MoonrakerWSClient
from Motion.Home import home
import time


def run_latency_test():
    """
    Home the printer, then execute Z moves in 1mm increments.
    Measures latency for each move command.
    """
    
    # Connect to Moonraker
    moonraker = MoonrakerWSClient("ws://192.168.8.146/websocket")
    moonraker.connect()
    print("[INIT] Connected to Moonraker")
    
    # Home the printer (blocking)
    print("[INIT] Homing printer...")
    home(moonraker, timeout=30.0)
    print("[INIT] Homing complete")
    
    # Move to starting position Z=10 (absolute)
    print("[INIT] Moving to starting position Z=10...")
    send_blocking_gcode(moonraker, "G90\nG0 Z10 F1200\nM400")
    print("[INIT] Starting position reached")
    
    # Print CSV header
    print("\n" + "=" * 80)
    print("LATENCY TEST RESULTS")
    print("=" * 80)
    print("step_index,z_delta_mm,send_time_s,receive_time_s,delta_t_s")
    
    step_index = 0
    
    # Phase 1: Z=10 → Z=20 in +1mm steps (10 steps)
    for i in range(10):
        step_index += 1
        z_delta = 1.0
        latency = execute_and_measure(moonraker, step_index, z_delta)
    
    # Phase 2: Z=20 → Z=0 in -1mm steps (20 steps)
    for i in range(20):
        step_index += 1
        z_delta = -1.0
        latency = execute_and_measure(moonraker, step_index, z_delta)
    
    print("=" * 80)
    print("[DONE] Latency test complete")
    
    # Cleanup
    moonraker.close()


def execute_and_measure(moonraker: MoonrakerWSClient, step_index: int, z_delta: float) -> float:
    """
    Execute a single relative Z move and measure round-trip latency.
    
    Args:
        moonraker: WebSocket client
        step_index: Step number for logging
        z_delta: Relative Z movement in mm
    
    Returns:
        Latency in seconds
    """
    # Build relative move command with M400 for synchronization
    gcode = f"Move z={z_delta:.3f}"
    
    # Record send timestamp (high resolution)
    send_time = time.perf_counter()
    
    # Send command and block until complete (M400 ensures motion completion)
    moonraker.call(
        "printer.gcode.script",
        {"script": gcode},
        timeout_s=10.0
    )
    
    # Record receive timestamp
    receive_time = time.perf_counter()
    
    # Compute latency
    delta_t = receive_time - send_time
    
    # Print CSV row
    print(f"{step_index},{z_delta:+.1f},{send_time:.6f},{receive_time:.6f},{delta_t:.6f}")
    
    return delta_t


def send_blocking_gcode(moonraker: MoonrakerWSClient, gcode: str, timeout: float = 10.0) -> None:
    """
    Send G-code and block until acknowledged.
    """
    moonraker.call(
        "printer.gcode.script",
        {"script": gcode},
        timeout_s=timeout
    )


if __name__ == "__main__":
    run_latency_test()
