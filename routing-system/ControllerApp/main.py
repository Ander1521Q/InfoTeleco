"""
main.py — ControllerApp entry point.
Reads host/port from config/controller_config.json and starts the controller.

Usage:
    python main.py
"""
import json
import sys
import os

# Allow running from the ControllerApp directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controller.controller_app_controller import ControllerAppController


def load_config(path: str = "config/controller_config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    config = load_config()
    controller = ControllerAppController(
        host=config["host"],
        port=config["port"]
    )
    controller.start()


if __name__ == "__main__":
    main()
