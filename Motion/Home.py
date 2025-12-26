from Motion.Moonraker_ws_v2 import MoonrakerWSClient

def home(ws_client: MoonrakerWSClient, timeout: float = 30.0) -> None:
        """
        Perform a full homing cycle.
        Blocking. Explicit use only (INIT / SHUTDOWN).
        """
        # Send homing command
        ws_client.call(
            "printer.gcode.script",
            {"script": "G28"},
            timeout_s=timeout
    )

    # Optionally wait until idle for safety
        if hasattr(ws_client, "wait_until_idle"):
            ok = ws_client.wait_until_idle(timeout_s=timeout)
            if not ok:
                raise RuntimeError("Homing completed but printer did not return to idle")