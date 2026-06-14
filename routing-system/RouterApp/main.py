"""
main.py — RouterApp entry point.

Usage:
    python main.py                        # uses config/router_config.json
    python main.py config/R2.json         # explicit config file
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controller.router_app_controller import RouterAppController


def main():
    config_path = (
        sys.argv[1] if len(sys.argv) > 1
        else "config/router_config.json"
    )
    RouterAppController(config_path).start()


if __name__ == "__main__":
    main()
