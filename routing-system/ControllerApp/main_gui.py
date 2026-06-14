"""
main_gui.py — ControllerApp GUI entry point.

Starts TCP server in background thread, opens Tkinter dashboard in main thread.
Wires gui.notify_disconnect/reconnect so the controller can trigger
immediate GUI refreshes when router connections change.

Usage:
    cd ControllerApp
    python main_gui.py
"""
import json
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controller.controller_app_controller import ControllerAppController
from gui.controller_gui  import ControllerGUI
from network.tcp_server  import TCPServer


def load_config(path: str = "config/controller_config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    config = load_config()
    host   = config["host"]
    port   = config["port"]

    # Build controller (handles TCP messages and DB)
    ctrl = ControllerAppController(host=host, port=port)

    # Build GUI first so we can pass it to controller BEFORE TCP starts
    gui = ControllerGUI(
        router_dao        = ctrl.router_dao,
        topology_dao      = ctrl.topology_dao,
        routing_table_dao = ctrl.routing_table_dao,
        routing_service   = ctrl.routing_service,
        host=host,
        port=port
    )

    # Wire GUI reference into controller for real-time notifications
    ctrl.gui = gui

    # Run startup reset BEFORE starting TCP server so GUI shows correct state
    ctrl._reset_all_routers_on_startup()

    # Start TCP server in background thread
    server = TCPServer(
        host=host,
        port=port,
        message_handler=ctrl.handle_message,
        disconnect_handler=ctrl.on_router_disconnect
    )
    threading.Thread(target=server.start, daemon=True).start()
    print(f"  TCP server started on {host}:{port}")
    print("  Opening dashboard...")

    # Run GUI in main thread (blocks until window is closed)
    gui.run()


if __name__ == "__main__":
    main()
