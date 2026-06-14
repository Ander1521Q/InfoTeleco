"""service/topology_service.py — Builds TOPOLOGY_UPDATE message."""
from model.router import Router


class TopologyService:
    @staticmethod
    def create_topology_message(router: Router) -> dict:
        return {
            "type":      "TOPOLOGY_UPDATE",
            "router_id": router.router_id,
            "neighbors": router.neighbors
        }
