"""
Router implementation for Centralized Routing System.
Acts as TCP client to controller, sends topology updates, and receives routing tables.
Author: Telecom Engineering Academic Project
Date: 2024
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import json
import threading
import time
from typing import Dict, Optional

from common.messages import MessageFactory, MessageValidator, MessageType
from common.logger import RoutingLogger
from router.routing_table import RoutingTable


class Router:
    """Router node in the centralized routing system."""

    def __init__(self, router_id: str, controller_host: str = '127.0.0.1',
                 controller_port: int = 8888, listen_port: int = None):
        self.router_id = router_id
        self.controller_host = controller_host
        self.controller_port = controller_port
        self.listen_port = listen_port or self._get_default_port(router_id)

        self.routing_table = RoutingTable(router_id)
        self.logger = RoutingLogger(f"Router-{router_id}")

        self.controller_socket: Optional[socket.socket] = None
        self.server_socket: Optional[socket.socket] = None
        self.running = False

        self.neighbors: Dict[str, float] = {}
        self.connected_to_controller = False

    def _get_default_port(self, router_id: str) -> int:
        try:
            router_num = int(router_id[1:])
            return 5000 + router_num
        except:
            return 5001

    def start(self):
        """Start the router and connect to controller."""
        self.running = True

        self._start_server()

        if self._connect_to_controller():
            if self._register():
                self._send_topology()
                self._cli_loop()

        self.logger.info(f"Router {self.router_id} stopped")

    def _start_server(self):
        """Start TCP server to receive routing tables from controller."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', self.listen_port))
            self.server_socket.listen(5)

            listener_thread = threading.Thread(target=self._listen_for_routing_tables)
            listener_thread.daemon = True
            listener_thread.start()

            self.logger.info(f"Router listening on 127.0.0.1:{self.listen_port}")

        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")

    def _listen_for_routing_tables(self):
        """Listen for incoming routing tables from controller."""
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                self.logger.debug(f"Connection from {client_address}")

                message_data = client_socket.recv(4096).decode('utf-8')

                if message_data:
                    self._process_routing_table_message(message_data)

                response = MessageFactory.create_acknowledgment(
                    MessageType.ROUTING_TABLE, "RECEIVED", f"Routing table received by {self.router_id}"
                )
                client_socket.sendall(response.encode('utf-8'))
                client_socket.close()

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in listener: {e}")
                time.sleep(0.1)

    def _process_routing_table_message(self, message_data: str):
        """Process incoming routing table message (FR-06)."""
        try:
            message = json.loads(message_data)

            if message.get('type') != MessageType.ROUTING_TABLE:
                self.logger.warning(f"Unexpected message type: {message.get('type')}")
                return

            if not MessageValidator.validate_routing_table(message):
                self.logger.error("Invalid routing table message")
                return

            router_id = message['router_id']

            if router_id != self.router_id:
                self.logger.warning(f"Routing table for {router_id} received, but this is {self.router_id}")
                return

            success = self.routing_table.update_table(message['routing_table'])

            if success:
                self.logger.info(f"Routing table updated with {self.routing_table.get_entry_count()} entries")
                self.logger.log_routing_table_delivery(self.router_id, self.routing_table.get_entry_count())
                print("\n" + self.routing_table.display_table())
            else:
                self.logger.error("Failed to update routing table")

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing routing table: {e}")

    def _connect_to_controller(self) -> bool:
        """Establish TCP connection to controller."""
        try:
            self.controller_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.controller_socket.settimeout(10)
            self.controller_socket.connect((self.controller_host, self.controller_port))
            self.connected_to_controller = True
            self.logger.log_connection("CONNECTED", self.controller_host, self.controller_port)
            return True

        except socket.error as e:
            self.logger.error(f"Failed to connect to controller: {e}")
            return False

    def _register(self) -> bool:
        """Register router with controller (FR-01)."""
        try:
            message = MessageFactory.create_register_router(
                self.router_id, '127.0.0.1', self.listen_port
            )

            self.controller_socket.sendall(message.encode('utf-8'))
            self.logger.debug(f"Sent registration: {message}")

            response_data = self.controller_socket.recv(4096).decode('utf-8')
            response = json.loads(response_data)

            if response.get('type') == MessageType.ACKNOWLEDGMENT:
                self.logger.info(f"Registration successful: {response.get('details')}")
                return True
            else:
                self.logger.error(f"Registration failed: {response}")
                return False

        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False

    def _send_topology(self):
        """Send neighbor/topology information to controller (FR-02)."""
        if not self.neighbors:
            self.logger.info("No neighbors configured. Use CLI to add neighbors.")
            return

        try:
            # Verificar que la conexión sigue activa
            if self.controller_socket is None:
                self.logger.error("No connection to controller")
                return

            neighbors_list = [
                {"neighbor_id": nid, "cost": cost}
                for nid, cost in self.neighbors.items()
            ]

            message = MessageFactory.create_topology_update(self.router_id, neighbors_list)

            self.logger.debug(f"Sending topology update: {message}")

            # Enviar mensaje
            self.controller_socket.sendall(message.encode('utf-8'))

            # Recibir respuesta con timeout
            self.controller_socket.settimeout(5)
            try:
                response_data = self.controller_socket.recv(4096).decode('utf-8')
                response = json.loads(response_data)

                if response.get('type') == MessageType.ACKNOWLEDGMENT:
                    self.logger.info(f"Topology update successful: {response.get('details')}")
                else:
                    self.logger.error(f"Topology update failed: {response}")
            except socket.timeout:
                self.logger.error("Timeout waiting for response from controller")
            except Exception as e:
                self.logger.error(f"Error receiving response: {e}")

        except socket.error as e:
            self.logger.error(f"Socket error sending topology: {e}")
            self.connected_to_controller = False
            self.controller_socket = None
        except Exception as e:
            self.logger.error(f"Error sending topology: {e}")

    def _cli_loop(self):
        """Command line interface for router administration (FR-07)."""
        self.logger.info(f"Router {self.router_id} CLI ready. Type 'help' for commands.")

        while self.running:
            try:
                command = input(f"\n[{self.router_id}] > ").strip().lower()

                if command == 'help':
                    self._print_help()
                elif command == 'table' or command == 'show':
                    self.routing_table.print_table()
                elif command == 'neighbors':
                    self._show_neighbors()
                elif command == 'add neighbor':
                    self._add_neighbor_interactive()
                elif command == 'update topology':
                    self._send_topology()
                elif command == 'status':
                    self._show_status()
                elif command == 'quit' or command == 'exit':
                    self.stop()
                    break
                elif command:
                    self.logger.info(f"Unknown command: {command}. Type 'help' for commands.")

            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n")
                continue
            except Exception as e:
                self.logger.error(f"CLI error: {e}")

    def _print_help(self):
        help_text = f"""
Router {self.router_id} Commands:
  help           - Show this help
  table / show   - Display routing table
  neighbors      - Show configured neighbors
  add neighbor   - Add neighbor interactively
  update topology - Send topology to controller
  status         - Show router status
  quit / exit    - Shutdown router
        """
        print(help_text)

    def _show_neighbors(self):
        if not self.neighbors:
            print("No neighbors configured.")
            return

        print(f"\nNeighbors of {self.router_id}:")
        print("-" * 40)
        for neighbor_id, cost in sorted(self.neighbors.items()):
            print(f"  {neighbor_id} (cost={cost})")

    def _add_neighbor_interactive(self):
        try:
            neighbor_id = input("Enter neighbor router ID (e.g., R2): ").strip().upper()

            if neighbor_id == self.router_id:
                print("Cannot add self as neighbor!")
                return

            try:
                cost = float(input("Enter link cost: ").strip())
                if cost < 0:
                    print("Cost cannot be negative!")
                    return
            except ValueError:
                print("Invalid cost value!")
                return

            self.neighbors[neighbor_id] = cost
            print(f"Added neighbor {neighbor_id} with cost {cost}")

            send_now = input("Send topology update to controller now? (y/n): ").strip().lower()
            if send_now == 'y':
                self._send_topology()

        except KeyboardInterrupt:
            print("\nOperation cancelled.")

    def _show_status(self):
        print(f"\nRouter {self.router_id} Status:")
        print("-" * 40)
        print(f"Controller: {self.controller_host}:{self.controller_port}")
        print(f"Listening on: 127.0.0.1:{self.listen_port}")
        print(f"Connected to controller: {self.connected_to_controller}")
        print(f"Routing table entries: {self.routing_table.get_entry_count()}")
        print(f"Configured neighbors: {len(self.neighbors)}")

    def stop(self):
        """Stop the router."""
        self.logger.info(f"Shutting down router {self.router_id}...")
        self.running = False

        if self.controller_socket:
            try:
                self.controller_socket.close()
            except:
                pass

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Router for Centralized Routing System')
    parser.add_argument('router_id', help='Router ID (e.g., R1, R2, R3, R4)')
    parser.add_argument('--controller-host', default='127.0.0.1', help='Controller host')
    parser.add_argument('--controller-port', type=int, default=8888, help='Controller port')
    parser.add_argument('--listen-port', type=int, help='Router listen port')

    args = parser.parse_args()

    router = Router(
        router_id=args.router_id,
        controller_host=args.controller_host,
        controller_port=args.controller_port,
        listen_port=args.listen_port
    )

    try:
        router.start()
    except KeyboardInterrupt:
        print("\nShutdown requested...")
        router.stop()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()