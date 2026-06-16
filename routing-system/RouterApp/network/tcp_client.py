"""
network/tcp_client.py
=====================
TCPClient: cliente TCP persistente con soporte para múltiples respuestas.

CORRECCIÓN BUG 2:
  El controller puede enviar VARIAS respuestas a un solo mensaje:
    TOPOLOGY_UPDATE → controller responde ACK + luego ROUTING_TABLE
  
  El método send_message() ahora tiene un modo "esperar tabla" que
  continúa leyendo hasta recibir el mensaje ROUTING_TABLE o agotar
  el timeout. Esto resuelve el problema de tablas vacías en R1 y R3.
"""
import socket
import json


class TCPClient:
    def __init__(self, controller_host: str, controller_port: int):
        self.controller_host = controller_host
        self.controller_port = controller_port
        self._sock   = None
        self._buffer = ""

    # ──────────────────────────────────────────────────── conexión
    def connect(self):
        """Abre una conexión TCP persistente al controller."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(10)
        self._sock.connect((self.controller_host, self.controller_port))
        self._sock.settimeout(None)   # modo bloqueante después de conectar
        self._buffer = ""

    def disconnect(self):
        """Cierra la conexión limpiamente."""
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self._buffer = ""

    def is_connected(self) -> bool:
        return self._sock is not None

    # ──────────────────────────────────────────────── envío/recepción
    def send_message(self, message: dict) -> dict:
        """
        Envía un mensaje JSON y retorna LA PRIMERA respuesta del controller.
        Para obtener la tabla de enrutamiento usa send_and_get_table().
        """
        data = (json.dumps(message) + "\n").encode("utf-8")
        self._sock.sendall(data)
        return self._recv_one()

    def send_and_get_table(self, message: dict) -> tuple:
        """
        CORRECCIÓN BUG 2: envía un mensaje y espera hasta recibir una
        respuesta ROUTING_TABLE, ignorando los ACK intermedios.

        El controller envía:
          1. ACK  (confirmación de registro/topología)
          2. ROUTING_TABLE (tabla calculada por Dijkstra)

        Retorna:
            (first_response, routing_table_response)
            first_response      = el ACK o el primer mensaje recibido
            routing_table_response = el ROUTING_TABLE o None si no llegó
        """
        data = (json.dumps(message) + "\n").encode("utf-8")
        self._sock.sendall(data)

        first   = None
        rt_resp = None

        # Leer hasta 5 mensajes buscando el ROUTING_TABLE
        for _ in range(5):
            try:
                # timeout corto para no bloquear si no hay más mensajes
                self._sock.settimeout(3.0)
                msg = self._recv_one()
                self._sock.settimeout(None)
            except (socket.timeout, OSError):
                self._sock.settimeout(None)
                break

            if first is None:
                first = msg

            if msg.get("type") == "ROUTING_TABLE":
                rt_resp = msg
                break
            # Si recibimos ERROR, parar
            if msg.get("type") == "ERROR":
                first = msg
                break

        return first or {}, rt_resp

    def _recv_one(self) -> dict:
        """Lee exactamente un mensaje JSON delimitado por newline."""
        while "\n" not in self._buffer:
            chunk = self._sock.recv(4096).decode("utf-8")
            if not chunk:
                raise ConnectionError("Controller closed the connection.")
            self._buffer += chunk

        line, self._buffer = self._buffer.split("\n", 1)
        return json.loads(line.strip())

    def recv_pending(self) -> list:
        """
        Lee todos los mensajes disponibles SIN bloquear.
        Útil para procesar tablas que llegaron mientras el router
        estaba ocupado con otro mensaje.
        """
        messages = []
        self._sock.settimeout(0.1)
        try:
            while True:
                chunk = self._sock.recv(4096).decode("utf-8")
                if not chunk:
                    break
                self._buffer += chunk
        except (socket.timeout, OSError):
            pass
        finally:
            self._sock.settimeout(None)

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return messages
