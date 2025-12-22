import websocket
import json

MOONRAKER_WS = "ws://192.168.8.127:7125/websocket"

def wait_for_complete(timeout=2.0):
    ws = websocket.create_connection(MOONRAKER_WS)
    ws.settimeout(timeout)

    # subscribe to gcode responses
    ws.send(json.dumps({
        "jsonrpc": "2.0",
        "method": "printer.objects.subscribe",
        "params": {"objects": {"gcode": ["responses"]}},
        "id": 1
    }))

    try:
        while True:
            msg = json.loads(ws.recv())

            if msg.get("method") == "notify_gcode_response":
                text = msg["params"][0].strip()
                if text == "// complete":
                    return
    finally:
        ws.close()
