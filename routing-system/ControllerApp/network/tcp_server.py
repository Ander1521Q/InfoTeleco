"""
network/tcp_server.py
=====================
TCPServer: multi-threaded TCP server para el controller.

CORRECCIÓN: ahora llama a disconnect_handler(router_id) cuando
un cliente cierra la conexión TCP, permitiendo al controller
marcar el router como DISCONNECTED en la BD y recalcular rutas.

Framing: newline-delimited JSON (cada mensaje termina con \n).
"""

import socket
import json
import logging
import threading


class TCPServer:
    def __init__(self, host: str, port: int,
                 message_handler,
                 disconnect_handler=None):
        """
        Args:
            message_handler:    fn(dict) -> dict  — procesa cada mensaje.
            disconnect_handler: fn(router_id: str) -> None  — llamado cuando
                                un cliente TCP cierra la conexión.
        """
        self.host               = host
        self.port               = port
        self.message_handler    = message_handler
        self.disconnect_handler = disconnect_handler
        self._server_socket     = None

        # router_id -> socket activo (para broadcasts futuros si se necesitan)
        self._active: dict      = {}
        self._lock              = threading.Lock()

    def start(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(20)
        print(f"  TCP server listening on {self.host}:{self.port} ...")

        while True:
            try:
                conn, addr = self._server_socket.accept()
                logging.info(f"New connection from {addr}")
                t = threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                t.start()
            except OSError:
                break

    def _handle_client(self, conn: socket.socket, addr: tuple):
        """Atiende una conexión cliente. Detecta desconexión y notifica."""
        buffer    = ""
        router_id = None          # se descubre al leer REGISTER_ROUTER

        try:
            while True:
                try:
                    chunk = conn.recv(4096).decode("utf-8")
                except (OSError, ConnectionResetError):
                    break

                if not chunk:
                    # Conexión cerrada limpiamente por el cliente
                    break

                buffer += chunk

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        message = json.loads(line)

                        # Guardar router_id en cuanto lo conocemos
                        if "router_id" in message and router_id is None:
                            router_id = message["router_id"]
                            with self._lock:
                                self._active[router_id] = conn

                        response = self.message_handler(message)
                        conn.sendall(
                            (json.dumps(response) + "\n").encode("utf-8")
                        )

                    except json.JSONDecodeError:
                        logging.error(f"Bad JSON from {addr}: {line[:80]}")
                        try:
                            conn.sendall(
                                (json.dumps({
                                    "type":    "ERROR",
                                    "message": "Invalid JSON"
                                }) + "\n").encode("utf-8")
                            )
                        except OSError:
                            break

                    except Exception as e:
                        logging.error(f"Handler error ({addr}): {e}")
                        try:
                            conn.sendall(
                                (json.dumps({
                                    "type":    "ERROR",
                                    "message": str(e)
                                }) + "\n").encode("utf-8")
                            )
                        except OSError:
                            break

        except Exception as e:
            logging.error(f"Client thread error ({addr}): {e}")

        finally:
            # ── DESCONEXIÓN DETECTADA ──────────────────────────────────────
            conn.close()
            if router_id:
                with self._lock:
                    self._active.pop(router_id, None)
                logging.info(f"Router '{router_id}' disconnected ({addr})")
                # Notificar al controller para actualizar BD y recalcular
                if self.disconnect_handler:
                    try:
                        self.disconnect_handler(router_id)
                    except Exception as e:
                        logging.error(
                            f"disconnect_handler error for {router_id}: {e}"
                        )
            else:
                logging.info(f"Unknown client disconnected: {addr}")

    def active_routers(self) -> list:
        """Retorna lista de router_ids con conexión TCP activa."""
        with self._lock:
            return list(self._active.keys())
