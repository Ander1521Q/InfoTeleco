"""
network/tcp_client.py
TCPClient: connects to the controller and exchanges newline-delimited JSON.
Keeps the socket open so the router can send multiple messages
(register, topology, link-cost updates) without reconnecting each time.
"""
import socket
import json


class TCPClient:
    def __init__(self, controller_host: str, controller_port: int):
        self.controller_host = controller_host
        self.controller_port = controller_port
        self._sock = None
        self._buffer = ""

    # ---------------------------------------------------------------- connect
    def connect(self):
        """Open a persistent TCP connection to the controller."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self.controller_host, self.controller_port))
        self._buffer = ""

    def disconnect(self):
        """Close the connection gracefully."""
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def is_connected(self) -> bool:
        return self._sock is not None

    # ---------------------------------------------------------- send/receive
    def send_message(self, message: dict) -> dict:
        """
        Send one JSON message (+ newline) and receive one JSON response.
        Opens a fresh connection if none is active (one-shot mode).
        """
        one_shot = not self.is_connected()
        if one_shot:
            self.connect()

        try:
            data = (json.dumps(message) + "\n").encode("utf-8")
            self._sock.sendall(data)
            return self._recv_one()
        finally:
            if one_shot:
                self.disconnect()

    def _recv_one(self) -> dict:
        """Read one newline-delimited response from the socket."""
        while "\n" not in self._buffer:
            chunk = self._sock.recv(4096).decode("utf-8")
            if not chunk:
                raise ConnectionError("Controller closed the connection.")
            self._buffer += chunk

        line, self._buffer = self._buffer.split("\n", 1)
        return json.loads(line.strip())
