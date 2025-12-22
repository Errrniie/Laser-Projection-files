# Manta/MantaMovement/Home.py
import requests
import json 
import websocket

MANTA_IP = "192.168.8.127"

def home_manta():
    try:
        requests.post(
            f"http://{MANTA_IP}/printer/gcode/script",
            json={"script": "G28"},
            timeout=0.2   # SHORT timeout — do not wait for homing
        )
    except requests.exceptions.RequestException:
        pass  # ignore timeout; homing is still happening