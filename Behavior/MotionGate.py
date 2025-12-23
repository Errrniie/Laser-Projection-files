# motion_gate.py
import threading

motion_lock = threading.Lock()
motion_in_flight = threading.Event()
motion_in_flight.clear()
