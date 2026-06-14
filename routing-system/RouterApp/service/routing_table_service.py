"""
service/routing_table_service.py
Stores the routing table locally as JSON and builds link-cost-update messages.
"""
import json
from pathlib import Path


class RoutingTableService:
    def __init__(self, data_path: str = "data/routing_table.json"):
        self.data_path = Path(data_path)

    def save_routing_table(self, router_id: str, table: list):
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump({"router_id": router_id, "routing_table": table},
                      f, indent=2)

    def load_routing_table(self) -> dict:
        if not self.data_path.exists():
            return {}
        with open(self.data_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def create_link_cost_update_message(
        router_id: str, neighbor_id: str, cost: float
    ) -> dict:
        return {
            "type":        "LINK_COST_UPDATE",
            "router_id":   router_id,
            "neighbor_id": neighbor_id,
            "cost":        cost
        }

    @staticmethod
    def create_router_down_message(router_id: str) -> dict:
        return {"type": "ROUTER_DOWN", "router_id": router_id}

    @staticmethod
    def create_router_up_message(router_id: str) -> dict:
        return {"type": "ROUTER_UP", "router_id": router_id}
