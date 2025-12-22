import requests

MANTA_IP = "192.168.8.127"
MOONRAKER_HTTP = f"http://{MANTA_IP}/printer/gcode/script"

def move_all(x=None, y=None, z=None, speed=1200):
    parts = []

    if x is not None:
        parts.append(f"X={x:.4f}")
    if y is not None:
        parts.append(f"Y={y:.4f}")
    if z is not None:
        parts.append(f"Z={z:.4f}")

    parts.append(f"SPEED={speed}")

    cmd = "MOVE " + " ".join(parts)

    requests.post(
        MOONRAKER_HTTP,
        json={"script": cmd},
        timeout=0.2
    )
