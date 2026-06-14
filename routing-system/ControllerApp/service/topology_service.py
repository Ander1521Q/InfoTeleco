"""service/topology_service.py — Handles TOPOLOGY_UPDATE and LINK_COST_UPDATE."""
from dao.topology_dao import TopologyDAO


class TopologyService:
    def __init__(self):
        self.topology_dao = TopologyDAO()

    def update_topology(self, message: dict) -> dict:
        router_id = message["router_id"]
        neighbors = message["neighbors"]
        self.topology_dao.save_topology(router_id, neighbors)
        return {
            "type": "ACK",
            "message": "Topology updated",
            "router_id": router_id
        }

    def update_link_cost(self, message: dict) -> dict:
        router_id   = message["router_id"]
        neighbor_id = message["neighbor_id"]
        cost        = float(message["cost"])

        updated = self.topology_dao.update_link_cost(router_id, neighbor_id, cost)

        if not updated:
            # Link didn't exist yet — create it in both directions
            self.topology_dao.save_topology(
                router_id,
                [{"neighbor_id": neighbor_id, "cost": cost}]
            )

        return {
            "type": "ACK",
            "message": "Link cost updated",
            "router_id": router_id,
            "neighbor_id": neighbor_id,
            "cost": cost
        }
