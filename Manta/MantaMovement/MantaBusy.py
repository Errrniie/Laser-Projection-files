# Manta/MantaMovement/WaitForXYZ.py
import time
import requests

MANTA_IP = "192.168.8.127"

X_TARGET = 5.75
Y_TARGET = 3.80
Z_TARGET = 10.0

def wait_for_xyz_at(
    x_target=X_TARGET,
    y_target=Y_TARGET,
    z_target=Z_TARGET,
    timeout_s=30
):
    t0 = time.time()

    while True:
        if time.time() - t0 > timeout_s:
            raise RuntimeError("Timeout waiting for X/Y/Z to reach targets")

        try:
            r = requests.get(
                f"http://{MANTA_IP}/printer/objects/query?toolhead",
                timeout=0.2
            ).json()

            pos = r["result"]["status"]["toolhead"]["position"]
            x = pos[0]
            y = pos[1]
            z = pos[2]

            if x == x_target and y == y_target and z == z_target:
                return

        except requests.exceptions.RequestException:
            pass

        time.sleep(0.1)
