"""dao/router_dao.py — Reads router config from a JSON file."""
import json


class RouterConfigDAO:
    def __init__(self, config_path: str = "config/router_config.json"):
        self.config_path = config_path

    def load_config(self) -> dict:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)
