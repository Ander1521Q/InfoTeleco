"""
Main Controller for Centralized Routing System.
Acts as TCP server handling router registrations, topology updates, and routing table distribution.
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import threading
import time
from typing import Dict, Optional
import signal
import json

from common.messages import MessageFactory, MessageValidator, MessageType
from common.logger import RoutingLogger
from controller.topology_manager import TopologyManager
from controller.routing_manager import RoutingManager


class RoutingController:
    """Centralized controller for the routing system."""

    def __init__(self, host: str = '127.0.0.1', port: int = 8888):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.running = False

        self.topology_manager = TopologyManager()
        self.routing_manager = RoutingManager(self.topology_manager)
        self.logger = RoutingLogger("Controller")

        self.active_connections: Dict[str, socket.socket] = {}

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def start(self):
        """Start the controller server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)

            self.running = True
            self.logger.info(f"Controller started on {self.host}:{self.port}")

            cli_thread = threading.Thread(target=self._cli_loop, daemon=True)
            cli_thread.start()

            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    self.logger.log_connection("ACCEPTED", client_address[0], client_address[1])

                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except socket.error as e:
                    if self.running:
                        self.logger.error(f"Socket accept error: {e}")
                    time.sleep(0.1)

        except Exception as e:
            self.logger.error(f"Failed to start controller: {e}")
            sys.exit(1)

    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """Handle client (router) connection."""
        try:
            # Recibir el primer mensaje
            message_data = client_socket.recv(4096).decode('utf-8')

            if not message_data:
                self.logger.warning(f"Empty message from {client_address}")
                client_socket.close()
                return

            message = MessageFactory.parse_message(message_data)
            message_type = message.get('type')

            if message_type == MessageType.REGISTER_ROUTER:
                # Procesar registro y mantener conexión abierta para más mensajes
                self._handle_registration_keep_alive(message, client_socket, client_address)
            else:
                self.logger.warning(f"Unexpected first message type: {message_type}")
                response = MessageFactory.create_error(f"Expected REGISTER_ROUTER first", 400)
                client_socket.sendall(response.encode('utf-8'))
                client_socket.close()

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON from {client_address}: {e}")
            response = MessageFactory.create_error("Invalid JSON format", 400)
            try:
                client_socket.sendall(response.encode('utf-8'))
            except:
                pass
            client_socket.close()
        except Exception as e:
            self.logger.error(f"Error handling client {client_address}: {e}")
            client_socket.close()

    def _handle_registration_keep_alive(self, message: dict, client_socket: socket.socket, client_address: tuple):
        """Handle router registration and keep connection alive for subsequent messages."""
        if not MessageValidator.validate_register_router(message):
            self.logger.error("Invalid registration message")
            response = MessageFactory.create_error("Invalid registration message", 400)
            client_socket.sendall(response.encode('utf-8'))
            client_socket.close()
            return

        router_id = message['router_id']
        ip = message['ip']
        port = message['port']

        success = self.topology_manager.register_router(router_id, ip, port)

        if success:
            self.logger.log_registration(router_id, ip, port)
            response = MessageFactory.create_acknowledgment(
                MessageType.REGISTER_ROUTER, "SUCCESS", f"Router {router_id} registered"
            )
            client_socket.sendall(response.encode('utf-8'))

            # Guardar la conexión para mensajes futuros
            self.active_connections[router_id] = client_socket

            # Ahora esperar más mensajes de este router (como TOPOLOGY_UPDATE)
            self._wait_for_messages(router_id, client_socket, client_address)
        else:
            response = MessageFactory.create_error(f"Failed to register {router_id}", 500)
            client_socket.sendall(response.encode('utf-8'))
            client_socket.close()

    def _wait_for_messages(self, router_id: str, client_socket: socket.socket, client_address: tuple):
        """Wait for additional messages from a registered router."""
        try:
            while self.running:
                # Configurar timeout para no bloquear indefinidamente
                client_socket.settimeout(30)
                try:
                    message_data = client_socket.recv(4096).decode('utf-8')

                    if not message_data:
                        self.logger.info(f"Router {router_id} disconnected")
                        break

                    message = MessageFactory.parse_message(message_data)
                    message_type = message.get('type')

                    if message_type == MessageType.TOPOLOGY_UPDATE:
                        self._handle_topology_update(message, client_socket, router_id)
                    else:
                        self.logger.warning(f"Unknown message from {router_id}: {message_type}")
                        response = MessageFactory.create_error(f"Unknown message type", 400)
                        client_socket.sendall(response.encode('utf-8'))

                except socket.timeout:
                    # Timeout normal, continuar esperando
                    continue
                except socket.error as e:
                    self.logger.info(f"Router {router_id} connection lost: {e}")
                    break

        except Exception as e:
            self.logger.error(f"Error in message loop for {router_id}: {e}")
        finally:
            # Limpiar conexión
            if router_id in self.active_connections:
                del self.active_connections[router_id]
            try:
                client_socket.close()
            except:
                pass

    def _handle_topology_update(self, message: dict, client_socket: socket.socket, router_id: str):
        """Handle topology update from router (FR-02)."""
        if not MessageValidator.validate_topology_update(message):
            self.logger.error("Invalid topology update message")
            response = MessageFactory.create_error("Invalid topology update", 400)
            client_socket.sendall(response.encode('utf-8'))
            return

        neighbors = message['neighbors']

        if not self.topology_manager.verify_router_exists(router_id):
            response = MessageFactory.create_error(f"Router {router_id} not registered", 404)
            client_socket.sendall(response.encode('utf-8'))
            return

        success = self.topology_manager.update_neighbors(router_id, neighbors)

        if success:
            self.logger.log_topology_update(router_id, neighbors)
            response = MessageFactory.create_acknowledgment(
                MessageType.TOPOLOGY_UPDATE, "SUCCESS", f"Topology updated for {router_id}"
            )
            client_socket.sendall(response.encode('utf-8'))

            if self.topology_manager.has_complete_topology():
                self.logger.info("Topology complete, recomputing routing tables...")
                self.routing_manager.compute_all_routing_tables()
                self.routing_manager.broadcast_routing_tables()
        else:
            response = MessageFactory.create_error(f"Failed to update topology for {router_id}", 500)
            client_socket.sendall(response.encode('utf-8'))

    def _cli_loop(self):
        """Command line interface for controller administration."""
        self.logger.info("Controller CLI ready. Type 'help' for commands.")

        while self.running:
            try:
                command = input("\n[Controller] > ").strip().lower()

                if command == 'help':
                    self._print_help()
                elif command == 'topology':
                    print(self.topology_manager.get_topology_summary())
                elif command == 'routers':
                    routers = self.topology_manager.get_all_routers()
                    print(f"Registered routers: {routers}")
                elif command == 'refresh':
                    self.routing_manager.refresh_all_routing_tables()
                elif command == 'quit' or command == 'exit':
                    self.logger.info("Shutting down controller...")
                    self.stop()
                    break
                elif command:
                    self.logger.info(f"Unknown command: {command}")

            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"CLI error: {e}")

    def _print_help(self):
        help_text = """
Available Commands:
  help      - Show this help message
  topology  - Display current network topology
  routers   - List all registered routers
  refresh   - Force refresh of all routing tables
  quit      - Shutdown controller
        """
        print(help_text)

    def stop(self):
        """Stop the controller server."""
        self.running = False

        for router_id, sock in self.active_connections.items():
            try:
                sock.close()
            except:
                pass

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        self.logger.info("Controller stopped")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Centralized Routing Controller')
    parser.add_argument('--host', default='127.0.0.1', help='Controller host address')
    parser.add_argument('--port', type=int, default=8888, help='Controller port number')

    args = parser.parse_args()

    controller = RoutingController(host=args.host, port=args.port)

    try:
        controller.start()
    except KeyboardInterrupt:
        print("\nShutdown requested...")
        controller.stop()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()