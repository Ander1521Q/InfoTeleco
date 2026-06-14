"""
view/controller_view.py
========================
ControllerCLIView: all output methods for the controller terminal.
Updated to show DISCONNECTED status and the new 'add' command.
"""


class ControllerCLIView:

    @staticmethod
    def show_start_message(ip: str, port: int):
        print("=" * 62)
        print("  Centralized Routing System — Controller")
        print(f"  Listening on {ip}:{port}")
        print("  Type 'help' for available commands.")
        print("=" * 62)

    @staticmethod
    def show_admin_menu():
        print("\n" + "-" * 62)
        print("  CONTROLLER ADMIN CLI")
        print("-" * 62)
        print("  topology                   Show network topology")
        print("  routers                    List all routers + status")
        print("  tables                     Show all routing tables")
        print("  table ROUTER               Show table for one router")
        print("  path ORIGIN DEST           Best path  (e.g. path R1 R4)")
        print("  down ROUTER                Mark INACTIVE and recalculate")
        print("  up ROUTER                  Mark ACTIVE and recalculate")
        print("  update R1 R2 COST          Update link cost + recalculate")
        print("  delete ROUTER              Delete router from network")
        print("  add ID IP PORT [NB:COST…]  Add new router with neighbors")
        print("                             e.g. add R5 127.0.0.1 5005 R1:3 R2:7")
        print("  help                       Show this menu")
        print("  exit                       Close admin CLI")
        print("-" * 62)

    @staticmethod
    def show_received_message(message: dict):
        t   = message.get("type", "?")
        rid = message.get("router_id", "")
        print(f"\n  ← IN  [{t}] from {rid}")

    @staticmethod
    def show_response(response: dict):
        t   = response.get("type", "?")
        rid = response.get("router_id", "")
        msg = response.get("message", "")
        print(f"  → OUT [{t}] to {rid}  {msg}")

    @staticmethod
    def show_registered_routers(routers):
        if not routers:
            print("\n  No routers registered yet.")
            return
        print(f"\n  {'Router':<10} {'IP':<16} {'Port':<8} {'Status'}")
        print(f"  {'-'*8}   {'-'*14}   {'-'*6}   {'-'*14}")
        for r in routers:
            s = r.status.upper()
            if s in ("ACTIVE", "ACTIVO"):
                dot = "●"
            elif s == "DISCONNECTED":
                dot = "✖"
            else:
                dot = "○"
            print(f"  {dot} {r.router_id:<8} {r.ip:<16} {r.port:<8} {r.status}")

    @staticmethod
    def show_topology(topology: dict):
        print("\n" + "=" * 50)
        print("         NETWORK TOPOLOGY")
        print("=" * 50)
        if not topology:
            print("  No topology available.")
            print("=" * 50)
            return
        seen, edges = set(), []
        for src, nbs in topology.items():
            for nb in nbs:
                key = tuple(sorted([src, nb["neighbor_id"]]))
                if key not in seen:
                    seen.add(key)
                    edges.append((key[0], key[1], nb["cost"]))
        for a, b, cost in sorted(edges):
            print(f"  {a} ↔ {b}   cost = {cost}")
        print("=" * 50)

    @staticmethod
    def show_routing_table(router_id: str, table: list):
        print(f"\n  Routing table for {router_id}:")
        if not table:
            print("    (empty)")
            return
        print(f"    {'Destination':<14} {'Next Hop':<12} {'Cost'}")
        print(f"    {'-'*12}   {'-'*10}   {'-'*6}")
        for e in table:
            print(f"    {e['destination']:<14} {e['next_hop']:<12} {e['cost']}")

    @staticmethod
    def show_all_routing_tables(tables: dict):
        if not tables:
            print("  No routing tables available yet.")
            return
        for rid in sorted(tables):
            ControllerCLIView.show_routing_table(rid, tables[rid])

    @staticmethod
    def show_best_path(origin: str, dest: str, path: list, cost):
        if not path:
            print(f"  No path found between {origin} and {dest}.")
            return
        print(f"\n  Best path  {origin} → {dest}")
        print(f"  Route    : {'  →  '.join(path)}")
        print(f"  Total cost: {cost}")

    @staticmethod
    def show_link_update(r1: str, r2: str, cost: float):
        print(f"  Link {r1} ↔ {r2} updated to cost = {cost}")

    @staticmethod
    def show_router_status_change(router_id: str, status: str):
        if status.upper() in ("ACTIVE", "ACTIVO"):
            symbol = "●"
        elif status.upper() == "DISCONNECTED":
            symbol = "✖"
        else:
            symbol = "○"
        print(f"  {symbol} Router {router_id} is now {status}.")

    @staticmethod
    def show_error(message: str):
        print(f"  [ERROR] {message}")

    @staticmethod
    def show_info(message: str):
        print(f"  {message}")
