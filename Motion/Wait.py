import websocket, json
import threading

MOONRAKER_WS = "ws://192.168.8.127:7125/websocket"

_ws = None
_ws_lock = threading.Lock()

def init_ws():
    global _ws
    _ws = websocket.create_connection(MOONRAKER_WS)
    _ws.send(json.dumps({
        "jsonrpc": "2.0",
        "method": "printer.objects.subscribe",
        "params": {"objects": {"gcode": ["responses"]}},
        "id": 1
    }))

def wait_for_complete():
    while True:
        msg = json.loads(_ws.recv())
        if msg.get("method") == "notify_gcode_response":
            if msg["params"][0].strip() == "// complete":
                return

