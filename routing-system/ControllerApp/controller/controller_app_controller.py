"""
controller/controller_app_controller.py
========================================
Controller principal — coordina TCP, DAOs, servicios y CLI.

CORRECCIONES Y MEJORAS:
  1. on_router_disconnect(): marca DISCONNECTED en BD y recalcula rutas.
  2. Nuevo mensaje ADD_ROUTER: permite agregar un router nuevo en runtime.
  3. CLI: nuevo comando 'add' para agregar routers dinámicamente.
  4. Estado DISCONNECTED separado de INACTIVE (INACTIVE = apagado por el admin,
     DISCONNECTED = perdió la conexión TCP).
"""

import logging
import threading

from dao.router_dao        import RouterDAO
from dao.topology_dao      import TopologyDAO
from dao.routing_table_dao import RoutingTableDAO
from service.registration_service import RouterRegistrationService
from service.topology_service      import TopologyService
from service.routing_service       import RoutingService
from service.message_service       import MessageService
from view.controller_view          import ControllerCLIView
from network.tcp_server            import TCPServer

logging.basicConfig(
    filename="controller.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class ControllerAppController:
    """
    Orchestrates the controller.
    TCP server runs in a daemon thread; admin CLI runs in the main thread.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

        self.view               = ControllerCLIView()
        self.router_dao         = RouterDAO()
        self.topology_dao       = TopologyDAO()
        self.routing_table_dao  = RoutingTableDAO()

        self.registration_service = RouterRegistrationService(self.router_dao)
        self.topology_service     = TopologyService()
        self.routing_service      = RoutingService(
            self.topology_dao, self.router_dao
        )
        self.message_service = MessageService()

        # TCP server reference (set in start())
        self._server: TCPServer | None = None

        # GUI reference — injected by main_gui.py after GUI is built
        # Allows the controller to trigger immediate GUI refreshes
        self.gui = None

    # ================================================================ start
    def start(self):
        self.view.show_start_message(self.host, self.port)
        logging.info(f"Controller started on {self.host}:{self.port}")

        # ── CORRECCIÓN Bug 3: al arrancar el controller, ningún router
        # está conectado todavía. Marcamos todos como DISCONNECTED para que
        # la GUI y las tablas no muestren routers fantasma de sesiones anteriores.
        self._reset_all_routers_on_startup()

        self._server = TCPServer(
            host=self.host,
            port=self.port,
            message_handler=self.handle_message,
            disconnect_handler=self.on_router_disconnect   # ← NEW
        )
        threading.Thread(target=self._server.start, daemon=True).start()
        self._run_admin_cli()

    # ============================================= disconnect handler (NEW)
    def on_router_disconnect(self, router_id: str):
        """
        Called by TCPServer when a router closes its TCP connection.

        Marks the router as DISCONNECTED in the DB and recalculates
        routing tables so other routers no longer route through it.
        """
        logging.info(f"Router '{router_id}' TCP connection lost — marking DISCONNECTED")
        self.view.show_info(
            f"\n  ○ Router '{router_id}' disconnected — marking DISCONNECTED, recalculating..."
        )

        # Mark as DISCONNECTED in DB (visible in GUI and CLI 'routers' command)
        self.router_dao.set_status(router_id, "DISCONNECTED")

        # Recalculate routes excluding the disconnected router
        self._recalculate_all()

        self.view.show_info(
            f"  Routes updated — '{router_id}' excluded from topology."
        )

        # Notify GUI immediately (don't wait for the 3s auto-refresh)
        if self.gui is not None:
            try:
                self.gui.notify_disconnect(router_id)
            except Exception:
                pass

    # ========================================== startup reset (Bug 3 fix)
    def _reset_all_routers_on_startup(self):
        """
        Al arrancar el controller, marca TODOS los routers existentes en la
        BD como DISCONNECTED.

        Esto soluciona el problema de routers "fantasma" que aparecen como
        ACTIVE en la GUI aunque no estén realmente conectados (datos de
        sesiones anteriores).  Cuando cada router se reconecte vía TCP y
        envíe REGISTER_ROUTER, su estado se restaura a ACTIVE automáticamente.
        """
        try:
            routers = self.router_dao.get_all_routers()
            for r in routers:
                self.router_dao.set_status(r.router_id, "DISCONNECTED")
            if routers:
                logging.info(
                    f"Startup: marked {len(routers)} router(s) as DISCONNECTED "
                    f"({[r.router_id for r in routers]})"
                )
                self.view.show_info(
                    f"  {len(routers)} router(s) from previous session marked "
                    "DISCONNECTED — waiting for reconnection."
                )
        except Exception as e:
            # No MySQL connection yet or empty DB — that's fine
            logging.warning(f"Could not reset router statuses on startup: {e}")

    # ======================================================== message handler
    def handle_message(self, message: dict) -> dict:
        """Entry point called by TCPServer for every incoming JSON message."""
        valid, reason = self.message_service.validate_message(message)
        if not valid:
            logging.error(f"Validation failed: {reason}")
            return {"type": "ERROR", "message": reason}

        self.view.show_received_message(message)
        logging.info(
            f"Message received: {message.get('type')} "
            f"from {message.get('router_id', '?')}"
        )

        msg_type = message.get("type")

        # ── FR-01: REGISTER_ROUTER ──────────────────────────────────────────
        if msg_type == "REGISTER_ROUTER":
            # If router was DISCONNECTED and reconnects, restore ACTIVE
            existing = self.router_dao.get_router_by_id(message["router_id"])
            if existing and existing.status == "DISCONNECTED":
                self.router_dao.set_status(message["router_id"], "ACTIVE")
                message["status"] = "ACTIVE"

            response = self.registration_service.register_router(message)
            logging.info(f"Router registered: {message['router_id']}")
            self.view.show_response(response)
            self.view.show_registered_routers(self.router_dao.get_all_routers())

            # Notify GUI of reconnect immediately
            if self.gui is not None:
                try:
                    self.gui.notify_reconnect(message["router_id"])
                except Exception:
                    pass
            return response

        # ── FR-02/FR-03: TOPOLOGY_UPDATE ────────────────────────────────────
        if msg_type == "TOPOLOGY_UPDATE":
            # Make sure the router is ACTIVE when it sends topology
            rid = message["router_id"]
            existing = self.router_dao.get_router_by_id(rid)
            if existing and existing.status in ("DISCONNECTED",):
                self.router_dao.set_status(rid, "ACTIVE")

            self.topology_service.update_topology(message)
            logging.info(f"Topology updated for: {rid}")
            return self._recalculate_and_respond(rid)

        # ── FR-08: LINK_COST_UPDATE ─────────────────────────────────────────
        if msg_type == "LINK_COST_UPDATE":
            self.topology_service.update_link_cost(message)
            rid = message["router_id"]
            logging.info(
                f"Link cost updated: {rid} ↔ "
                f"{message['neighbor_id']} = {message['cost']}"
            )
            return self._recalculate_and_respond(rid)

        # ── ROUTER_DOWN (sent by router CLI) ────────────────────────────────
        if msg_type == "ROUTER_DOWN":
            rid = message["router_id"]
            self.router_dao.set_status(rid, "INACTIVE")
            self._recalculate_all()
            logging.info(f"Router {rid} set INACTIVE by itself")
            return {"type": "ACK", "message": f"Router {rid} marked INACTIVE"}

        # ── ROUTER_UP (sent by router CLI) ──────────────────────────────────
        if msg_type == "ROUTER_UP":
            rid = message["router_id"]
            self.router_dao.set_status(rid, "ACTIVE")
            self._recalculate_all()
            logging.info(f"Router {rid} reactivated by itself")
            return {"type": "ACK", "message": f"Router {rid} marked ACTIVE"}

        return {"type": "ERROR", "message": f"Unknown type: '{msg_type}'"}

    # ============================================ recalculate and respond
    def _recalculate_and_respond(self, requested_router_id: str) -> dict:
        """Run Dijkstra for all active routers, persist, return table."""
        tables = self.routing_service.generate_all_routing_tables()

        for rid, table in tables.items():
            self.routing_table_dao.save_routing_table(rid, table)
            self.view.show_routing_table(rid, table)
            logging.info(f"Routing table saved for: {rid}")

        if requested_router_id not in tables:
            msg = (
                f"Router '{requested_router_id}' is not active "
                "or not reachable."
            )
            logging.warning(msg)
            return {
                "type":      "ROUTING_TABLE",
                "router_id": requested_router_id,
                "routing_table": [],
                "table":     [],
                "message":   msg
            }

        table = tables[requested_router_id]
        return {
            "type":          "ROUTING_TABLE",
            "router_id":     requested_router_id,
            "routing_table": table,
            "table":         table
        }

    def _recalculate_all(self):
        """Recalculate all tables for active routers and persist."""
        tables = self.routing_service.generate_all_routing_tables()
        for rid, table in tables.items():
            self.routing_table_dao.save_routing_table(rid, table)
            self.view.show_routing_table(rid, table)
            logging.info(f"Routing table recalculated for: {rid}")
        if not tables:
            self.view.show_info("No active routers — no routes calculated.")

    # ================================================================== CLI
    def _run_admin_cli(self):
        """
        Interactive administrator CLI.

        Commands:
          topology              – show network topology
          routers               – list all routers (with status)
          tables                – show all routing tables
          table ROUTER          – show table for one router
          path R1 R4            – show best path
          down ROUTER           – mark INACTIVE and recalculate
          up ROUTER             – mark ACTIVE and recalculate
          update R1 R2 COST     – update link cost and recalculate
          delete ROUTER         – delete router from network
          add ID IP PORT N1:C1 … – add a new router with neighbors
          help                  – show this menu
          exit                  – close CLI (server keeps running)
        """
        self.view.show_admin_menu()

        while True:
            try:
                raw = input("Controller-Admin> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Closing admin CLI.")
                break

            if not raw:
                continue

            parts = raw.split()
            cmd   = parts[0].lower()

            try:

                # ── topology ──────────────────────────────────────────────
                if cmd in ("topology", "topo"):
                    self.view.show_topology(self.topology_dao.get_topology())

                # ── routers ───────────────────────────────────────────────
                elif cmd == "routers":
                    self.view.show_registered_routers(
                        self.router_dao.get_all_routers()
                    )

                # ── tables ────────────────────────────────────────────────
                elif cmd == "tables":
                    tables = self.routing_service.generate_all_routing_tables()
                    if not tables:
                        self.view.show_info("No routing tables yet.")
                    else:
                        self.view.show_all_routing_tables(tables)

                # ── table ROUTER ──────────────────────────────────────────
                elif cmd == "table":
                    if len(parts) < 2:
                        self.view.show_info("Usage: table ROUTER_ID")
                    else:
                        rid   = parts[1].upper()
                        table = self.routing_table_dao.get_routing_table(rid)
                        self.view.show_routing_table(rid, table)

                # ── path R1 R4 ────────────────────────────────────────────
                elif cmd == "path":
                    if len(parts) != 3:
                        self.view.show_info("Usage: path ORIGIN DESTINATION")
                    else:
                        origin = parts[1].upper()
                        dest   = parts[2].upper()
                        path, cost = self.routing_service.get_full_path(
                            origin, dest
                        )
                        self.view.show_best_path(origin, dest, path, cost)
                        logging.info(f"Path {origin}->{dest}: {path} cost={cost}")

                # ── down ROUTER ───────────────────────────────────────────
                elif cmd == "down":
                    if len(parts) < 2:
                        self.view.show_info("Usage: down ROUTER_ID")
                    else:
                        rid = parts[1].upper()
                        if not self.router_dao.get_router_by_id(rid):
                            self.view.show_error(f"Router '{rid}' not found.")
                        else:
                            self.router_dao.set_status(rid, "INACTIVE")
                            self.view.show_router_status_change(rid, "INACTIVE")
                            self._recalculate_all()
                            logging.info(f"Router marked INACTIVE: {rid}")

                # ── up ROUTER ─────────────────────────────────────────────
                elif cmd == "up":
                    if len(parts) < 2:
                        self.view.show_info("Usage: up ROUTER_ID")
                    else:
                        rid = parts[1].upper()
                        if not self.router_dao.get_router_by_id(rid):
                            self.view.show_error(f"Router '{rid}' not found.")
                        else:
                            self.router_dao.set_status(rid, "ACTIVE")
                            self.view.show_router_status_change(rid, "ACTIVE")
                            self._recalculate_all()
                            logging.info(f"Router reactivated: {rid}")

                # ── update R1 R2 COST ─────────────────────────────────────
                elif cmd == "update":
                    if len(parts) != 4:
                        self.view.show_info(
                            "Usage: update ROUTER_A ROUTER_B NEW_COST"
                        )
                    else:
                        r1, r2 = parts[1].upper(), parts[2].upper()
                        try:
                            cost = float(parts[3])
                            if cost < 0:
                                raise ValueError()
                        except ValueError:
                            self.view.show_error("COST must be >= 0")
                        else:
                            self.topology_dao.update_link_cost(r1, r2, cost)
                            self.view.show_link_update(r1, r2, cost)
                            self._recalculate_all()
                            logging.info(f"CLI link update {r1}↔{r2} cost={cost}")

                # ── delete ROUTER ─────────────────────────────────────────
                elif cmd == "delete":
                    if len(parts) < 2:
                        self.view.show_info("Usage: delete ROUTER_ID")
                    else:
                        rid = parts[1].upper()
                        self.router_dao.delete_router(rid)
                        self.view.show_info(
                            f"Router '{rid}' deleted. Recalculating..."
                        )
                        self._recalculate_all()
                        logging.info(f"Router deleted: {rid}")

                # ── add ID IP PORT N1:C N2:C … ────────────────────────────
                elif cmd == "add":
                    self._cli_add_router(parts[1:])

                # ── help ──────────────────────────────────────────────────
                elif cmd in ("help", "?", ""):
                    self.view.show_admin_menu()

                # ── exit ──────────────────────────────────────────────────
                elif cmd in ("exit", "quit"):
                    print("  CLI closed. TCP server continues running.")
                    break

                else:
                    self.view.show_info(
                        f"Unknown command: '{cmd}'. Type 'help'."
                    )

            except Exception as err:
                logging.error(f"CLI error: {err}")
                self.view.show_error(str(err))

    # ── add router helper ──────────────────────────────────────────────────
    def _cli_add_router(self, args: list):
        """
        add R5 127.0.0.1 5005 R1:3 R2:7
        Adds a new router to the DB with given neighbors and recalculates.
        The physical router still needs to connect via TCP to be reachable,
        but this pre-registers it and sets up the topology links.
        """
        if len(args) < 3:
            self.view.show_info(
                "Usage: add ROUTER_ID IP PORT [NEIGHBOR:COST ...]\n"
                "  e.g. add R5 127.0.0.1 5005 R1:3 R2:7"
            )
            return

        rid = args[0].upper()
        ip  = args[1]
        try:
            port = int(args[2])
        except ValueError:
            self.view.show_error("PORT must be an integer.")
            return

        # Parse optional neighbor:cost pairs
        neighbors = []
        for token in args[3:]:
            if ":" not in token:
                self.view.show_error(
                    f"Neighbor format must be NEIGHBOR_ID:COST, got '{token}'"
                )
                return
            nb_id, cost_str = token.split(":", 1)
            try:
                cost = float(cost_str)
            except ValueError:
                self.view.show_error(f"Invalid cost for {nb_id}: '{cost_str}'")
                return
            neighbors.append({"neighbor_id": nb_id.upper(), "cost": cost})

        # Save to DB
        from model.router import Router
        router = Router(router_id=rid, ip=ip, port=port, status="ACTIVE")
        self.router_dao.save_router(router)

        if neighbors:
            self.topology_dao.save_topology(rid, neighbors)

        self.view.show_info(
            f"Router '{rid}' added ({ip}:{port}) "
            f"with {len(neighbors)} neighbor(s)."
        )
        logging.info(f"Router added via CLI: {rid} {ip}:{port} neighbors={neighbors}")

        self._recalculate_all()
        self.view.show_info(
            f"Note: '{rid}' must now connect via RouterApp to exchange packets."
        )
