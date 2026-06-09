"""
Topology Manager for the Centralized Routing System.
Maintains network topology and router registration information.
Author: Telecom Engineering Academic Project
Date: 2024
"""

import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import os


@dataclass
class RouterInfo:
    """Data class for router information."""
    router_id: str
    ip: str
    port: int
    registered_at: str
    last_update: str
    neighbors: Dict[str, float]

    def to_dict(self) -> dict:
        return {
            "router_id": self.router_id,
            "ip": self.ip,
            "port": self.port,
            "registered_at": self.registered_at,
            "last_update": self.last_update,
            "neighbors": self.neighbors
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'RouterInfo':
        return cls(
            router_id=data["router_id"],
            ip=data["ip"],
            port=data["port"],
            registered_at=data["registered_at"],
            last_update=data["last_update"],
            neighbors=data["neighbors"]
        )


class TopologyManager:
    """Manages the network topology and router registrations."""

    def __init__(self, routers_file: str = "data/routers.json",
                 topology_file: str = "data/topology.json"):
        self.routers: Dict[str, RouterInfo] = {}
        self.topology: Dict[str, Dict[str, float]] = {}
        self.routers_file = routers_file
        self.topology_file = topology_file

        os.makedirs(os.path.dirname(routers_file), exist_ok=True)
        self._load_routers()
        self._load_topology()

    def _load_routers(self):
        if os.path.exists(self.routers_file):
            try:
                with open(self.routers_file, 'r') as f:
                    data = json.load(f)
                    for router_id, router_data in data.items():
                        self.routers[router_id] = RouterInfo.from_dict(router_data)
            except (json.JSONDecodeError, IOError):
                pass

    def _load_topology(self):
        if os.path.exists(self.topology_file):
            try:
                with open(self.topology_file, 'r') as f:
                    self.topology = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_routers(self):
        try:
            routers_dict = {rid: r.to_dict() for rid, r in self.routers.items()}
            with open(self.routers_file, 'w') as f:
                json.dump(routers_dict, f, indent=2)
        except IOError:
            pass

    def _save_topology(self):
        try:
            with open(self.topology_file, 'w') as f:
                json.dump(self.topology, f, indent=2)
        except IOError:
            pass

    def register_router(self, router_id: str, ip: str, port: int) -> bool:
        current_time = datetime.now().isoformat()

        if router_id in self.routers:
            self.routers[router_id].ip = ip
            self.routers[router_id].port = port
            self.routers[router_id].last_update = current_time
        else:
            self.routers[router_id] = RouterInfo(
                router_id=router_id,
                ip=ip,
                port=port,
                registered_at=current_time,
                last_update=current_time,
                neighbors={}
            )

        if router_id not in self.topology:
            self.topology[router_id] = {}

        self._save_routers()
        self._save_topology()
        return True

    def update_neighbors(self, router_id: str, neighbors: List[Dict]) -> bool:
        if router_id not in self.routers:
            return False

        current_time = datetime.now().isoformat()
        self.routers[router_id].last_update = current_time
        self.routers[router_id].neighbors.clear()

        for neighbor in neighbors:
            neighbor_id = neighbor["neighbor_id"]
            cost = float(neighbor["cost"])
            self.routers[router_id].neighbors[neighbor_id] = cost
            self.topology[router_id][neighbor_id] = cost

            if neighbor_id not in self.topology:
                self.topology[neighbor_id] = {}

        self._save_routers()
        self._save_topology()
        return True

    def update_link_cost(self, router1: str, router2: str, new_cost: float) -> bool:
        if router1 not in self.topology or router2 not in self.topology:
            return False

        if router2 in self.topology[router1]:
            self.topology[router1][router2] = new_cost

        if router1 in self.topology[router2]:
            self.topology[router2][router1] = new_cost

        if router1 in self.routers and router2 in self.routers[router1].neighbors:
            self.routers[router1].neighbors[router2] = new_cost

        if router2 in self.routers and router1 in self.routers[router2].neighbors:
            self.routers[router2].neighbors[router1] = new_cost

        self._save_topology()
        self._save_routers()
        return True

    def get_router(self, router_id: str) -> Optional[RouterInfo]:
        return self.routers.get(router_id)

    def get_all_routers(self) -> List[str]:
        return list(self.routers.keys())

    def get_topology(self) -> Dict[str, Dict[str, float]]:
        return self.topology

    def verify_router_exists(self, router_id: str) -> bool:
        return router_id in self.routers

    def get_router_count(self) -> int:
        return len(self.routers)

    def get_topology_summary(self) -> str:
        summary_lines = ["Network Topology Summary:", "-" * 40]

        for source, destinations in self.topology.items():
            for dest, cost in destinations.items():
                if source < dest:
                    summary_lines.append(f"{source} <--{cost}--> {dest}")

        summary_lines.append(f"\nTotal Routers: {len(self.routers)}")
        return "\n".join(summary_lines)

    def has_complete_topology(self) -> bool:
        if len(self.routers) < 2:
            return False

        for router_id in self.routers:
            if not self.topology.get(router_id, {}):
                return False

        return True