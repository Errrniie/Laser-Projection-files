import socket

ESP32_IP = "192.168.8.186"
PORT = 9000

START_BYTE = 0xAA
PROTO_VER  = 0x01

CMD_OFF  = 0x00
CMD_ARM  = 0x01
CMD_FIRE = 0x02


class Controller:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ESP32_IP, PORT))
        self.armed = False

    def _send(self, cmd, val=0):
        pkt = bytes([START_BYTE, PROTO_VER, cmd, val, 0x00])
        self.sock.sendall(pkt)

    def set_laser(self, enable: bool):
        if enable:
            if not self.armed:
                self._send(CMD_ARM)
                self.armed = True
            self._send(CMD_FIRE)
        else:
            self._send(CMD_OFF)
            self.armed = False
