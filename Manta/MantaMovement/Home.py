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

MOONRAKER_WS = "ws://192.168.8.127:7125/websocket"

def wait_for_complete():
    ws = websocket.create_connection(MOONRAKER_WS)

    # subscribe to gcode responses
    ws.send(json.dumps({
        "jsonrpc": "2.0",
        "method": "printer.objects.subscribe",
        "params": {"objects": {"gcode": ["responses"]}},
        "id": 1
    }))

    while True:
        msg = json.loads(ws.recv())

        if msg.get("method") == "notify_gcode_response":
            text = msg["params"][0]
            print("KLIPPER:", text)

            if "complete" in text:
                ws.close()
                return