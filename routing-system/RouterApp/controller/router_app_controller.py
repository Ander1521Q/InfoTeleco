"""
controller/router_app_controller.py
RouterAppController: coordinates the router lifecycle and CLI.

Lifecycle:
  1. Load config JSON.
  2. Connect to controller (persistent socket).
  3. Send REGISTER_ROUTER → wait for ACK.
  4. Send TOPOLOGY_UPDATE → receive ROUTING_TABLE.
  5. Enter interactive CLI loop.

CLI commands:
  show                      – display current routing table
  update-cost NEIGHBOR COST – send LINK_COST_UPDATE, receive new table
  down                      – send ROUTER_DOWN to controller
  up                        – send ROUTER_UP to controller
  help                      – show menu
  exit                      – disconnect and quit
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.router                     import Router
from dao.router_dao                   import RouterConfigDAO
from service.registration_service     import RegistrationService
from service.topology_service         import TopologyService
from service.routing_table_service    import RoutingTableService
from network.tcp_client               import TCPClient
from view.router_view                 import RouterCLIView


class RouterAppController:

    def __init__(self, config_path: str = "config/router_config.json"):
        self.config_dao            = RouterConfigDAO(config_path)
        self.registration_service  = RegistrationService()
        self.topology_service      = TopologyService()
        self.routing_table_service = RoutingTableService()
        self.view                  = RouterCLIView()

    # ================================================================= start
    def start(self):
        config = self.config_dao.load_config()

        router = Router(
            router_id = config["router"]["router_id"],
            ip        = config["router"]["ip"],
            port      = config["router"]["port"],
            neighbors = config["router"]["neighbors"],
            status    = config["router"].get("status", "ACTIVE")
        )

        ctrl_host = config["controller"]["host"]
        ctrl_port = config["controller"]["port"]

        self.view.show_start_message(router.router_id, router.ip, router.port)

        # --- build messages ---
        reg_msg  = self.registration_service.create_registration_message(router)
        topo_msg = self.topology_service.create_topology_message(router)

        # --- open persistent connection ---
        client = TCPClient(controller_host=ctrl_host, controller_port=ctrl_port)

        try:
            client.connect()
            self.view.show_info(
                f"Connected to controller at {ctrl_host}:{ctrl_port}"
            )
        except ConnectionRefusedError:
            self.view.show_error(
                "Connection refused. Make sure ControllerApp is running."
            )
            return
        except Exception as e:
            self.view.show_error(str(e))
            return

        try:
            # Step 1: Register
            self.view.show_registration_message(reg_msg)
            reg_resp = client.send_message(reg_msg)
            self.view.show_controller_response(reg_resp)

            if reg_resp.get("type") == "ERROR":
                self.view.show_error(
                    f"Registration rejected: {reg_resp.get('message','')}"
                )
                return

            # Step 2: Send topology
            self.view.show_topology_message(topo_msg)
            topo_resp = client.send_message(topo_msg)
            self.view.show_controller_response(topo_resp)

            # Step 3: Handle routing table
            table = self._extract_table(topo_resp)
            if table is not None:
                router.routing_table = table
                self.routing_table_service.save_routing_table(
                    router.router_id, table
                )
                self.view.show_routing_table(router.router_id, table)
                self.view.show_routing_table_saved(
                    str(self.routing_table_service.data_path)
                )

            # Step 4: Interactive CLI
            self._run_cli(router, client)

        except (ConnectionResetError, BrokenPipeError, ConnectionError) as e:
            self.view.show_error(f"Connection lost: {e}")
        except Exception as e:
            self.view.show_error(str(e))
        finally:
            client.disconnect()
            self.view.show_info("Disconnected from controller.")

    # ============================================================= CLI loop
    def _run_cli(self, router: Router, client: TCPClient):
        self.view.show_menu()

        while True:
            raw = self.view.ask_command(router.router_id)
            if not raw:
                continue

            parts = raw.split()
            cmd   = parts[0].lower()

            # ---- show ----
            if cmd == "show":
                self.view.show_routing_table(
                    router.router_id, router.routing_table
                )

            # ---- update-cost NEIGHBOR COST ----
            elif cmd == "update-cost":
                if len(parts) != 3:
                    self.view.show_error("Usage: update-cost NEIGHBOR_ID COST")
                    continue
                neighbor_id = parts[1].upper()
                try:
                    cost = float(parts[2])
                    if cost < 0:
                        raise ValueError("negative")
                except ValueError:
                    self.view.show_error("COST must be a non-negative number.")
                    continue

                msg = self.routing_table_service.create_link_cost_update_message(
                    router.router_id, neighbor_id, cost
                )
                self.view.show_info(
                    f"Sending LINK_COST_UPDATE: {router.router_id} ↔ "
                    f"{neighbor_id} = {cost}"
                )
                resp  = client.send_message(msg)
                self.view.show_controller_response(resp)
                table = self._extract_table(resp)
                if table is not None:
                    router.routing_table = table
                    self.routing_table_service.save_routing_table(
                        router.router_id, table
                    )
                    self.view.show_routing_table(router.router_id, table)

            # ---- down ----
            elif cmd == "down":
                msg  = self.routing_table_service.create_router_down_message(
                    router.router_id
                )
                self.view.show_info(
                    f"Signalling controller: {router.router_id} → INACTIVE"
                )
                resp = client.send_message(msg)
                self.view.show_controller_response(resp)

            # ---- up ----
            elif cmd == "up":
                msg  = self.routing_table_service.create_router_up_message(
                    router.router_id
                )
                self.view.show_info(
                    f"Signalling controller: {router.router_id} → ACTIVE"
                )
                resp = client.send_message(msg)
                self.view.show_controller_response(resp)

            # ---- help ----
            elif cmd in ("help", "?"):
                self.view.show_menu()

            # ---- exit ----
            elif cmd in ("exit", "quit"):
                break

            else:
                self.view.show_error(
                    f"Unknown command '{cmd}'. Type 'help'."
                )

    # =========================================================== helpers
    @staticmethod
    def _extract_table(response: dict):
        """Return the routing table list from a ROUTING_TABLE response."""
        if response.get("type") != "ROUTING_TABLE":
            return None
        return response.get("routing_table", response.get("table", []))
