from Motion.Moonraker_ws import MoonrakerWSClient

def home_manta(ws_client: MoonrakerWSClient):
    try:
        ws_client.call(
            "printer.gcode.script",
            {"script": "G28"},
        )
    except Exception:
        pass # a timeout is expected here
