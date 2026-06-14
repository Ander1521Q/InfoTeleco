"""
view/router_view.py
RouterCLIView: all display methods for the router terminal.
FR-07 (routing table display) + extended router CLI.
"""


class RouterCLIView:

    @staticmethod
    def show_start_message(router_id: str, ip: str, port: int):
        print("=" * 60)
        print(f"  RouterApp — {router_id}  ({ip}:{port})")
        print("  Type 'help' for available commands.")
        print("=" * 60)

    @staticmethod
    def show_registration_message(message: dict):
        print(f"\n  → Sending REGISTER_ROUTER  (id={message['router_id']},"
              f" ip={message['ip']}, port={message['port']})")

    @staticmethod
    def show_topology_message(message: dict):
        nb_list = ", ".join(
            f"{n['neighbor_id']}:{n['cost']}"
            for n in message.get("neighbors", [])
        )
        print(f"  → Sending TOPOLOGY_UPDATE  neighbors=[{nb_list}]")

    @staticmethod
    def show_controller_response(response: dict):
        t   = response.get("type", "?")
        msg = response.get("message", "")
        print(f"  ← [{t}] {msg}")

    @staticmethod
    def show_routing_table(router_id: str, table: list):
        print("\n" + "=" * 50)
        print(f"  ROUTING TABLE — {router_id}")
        print("=" * 50)
        if not table:
            print("  (no entries)")
        else:
            print(f"  {'Destination':<14} {'Next Hop':<12} {'Cost'}")
            print(f"  {'-'*12}   {'-'*10}   {'-'*6}")
            for e in table:
                print(f"  {e['destination']:<14} {e['next_hop']:<12} {e['cost']}")
        print("=" * 50)

    @staticmethod
    def show_routing_table_saved(path: str):
        print(f"  Routing table saved locally → {path}")

    @staticmethod
    def show_menu():
        print("\n  Commands:")
        print("  show                        Display current routing table")
        print("  update-cost NEIGHBOR COST   Update a link cost")
        print("  down                        Signal this router as INACTIVE")
        print("  up                          Signal this router as ACTIVE")
        print("  help                        Show this menu")
        print("  exit                        Disconnect and quit")

    @staticmethod
    def ask_command(router_id: str) -> str:
        return input(f"  Router-{router_id}> ").strip()

    @staticmethod
    def show_error(message: str):
        print(f"  [ERROR] {message}")

    @staticmethod
    def show_info(message: str):
        print(f"  {message}")
