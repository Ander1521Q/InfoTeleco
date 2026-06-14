"""
main_gui.py — RouterApp GUI entry point.

Opens a single window that manages all 4 routers simultaneously.

Usage:
    python main_gui.py        (from RouterApp/)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.router_manager_gui import RouterManagerGUI


def main():
    print("  Starting Router Manager GUI...")
    print("  Make sure ControllerApp is running first!")
    app = RouterManagerGUI()
    app.run()


if __name__ == "__main__":
    main()
