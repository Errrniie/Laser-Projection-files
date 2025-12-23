from __future__ import annotations
from Motion.Moonraker_ws import MoonrakerWSClient

def get_motor_positions(ws_client: MoonrakerWSClient, decimal_places: int = 3) -> dict | None:
    """
    Retrieve and format the X, Y, Z positions from the Manta board.
    
    Parameters:
        ws_client (MoonrakerWSClient): The WebSocket client.
        decimal_places (int): Number of decimal places to format to
    
    Returns:
        dict: Dictionary with formatted X, Y, Z positions as strings
        None: If an error occurs during retrieval
    """
    try:
        # Query the toolhead position
        response = ws_client.call(
            "printer.objects.query",
            {"objects": {"toolhead": None}},
        )
        
        toolhead = response["result"]["status"]["toolhead"]
        
        # Get raw positions
        x_raw, y_raw, z_raw = toolhead["position"]
        
        # Format positions
        fmt_string = f"{{:.{decimal_places}f}}"
        
        return {
            "x": fmt_string.format(x_raw),
            "y": fmt_string.format(y_raw),
            "z": fmt_string.format(z_raw),
            "x_raw": x_raw,  # Keep raw values for calculations
            "y_raw": y_raw,
            "z_raw": z_raw
        }
    except Exception as e:
        print(f"Error retrieving positions: {e}")
        return None
