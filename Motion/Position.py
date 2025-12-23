import requests

MANTA_IP = "192.168.8.146"

def get_motor_positions(decimal_places=3):
    """
    Retrieve and format the X, Y, Z positions from the Manta board.
    
    Parameters:
        decimal_places (int): Number of decimal places to format to
    
    Returns:
        dict: Dictionary with formatted X, Y, Z positions as strings
        None: If an error occurs during retrieval
    """
    try:
        # Query the toolhead position
        r = requests.get(
            f"http://{MANTA_IP}:7125/printer/objects/query?toolhead",
            timeout=2  # 2-second timeout
        )
        r.raise_for_status()  # Raise exception for HTTP errors
        
        data = r.json()
        toolhead = data["result"]["status"]["toolhead"]
        
        # Get raw positions
        x_raw = toolhead["position"][0]
        y_raw = toolhead["position"][1]
        z_raw = toolhead["position"][2]
        
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
    except requests.exceptions.RequestException as e:
        print(f"Network error retrieving positions: {e}")
        return None
    except KeyError as e:
        print(f"Data structure error: Missing key {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None