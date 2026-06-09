"""
Routing Table management for router nodes.
Stores and manages routing information received from controller.
Author: Telecom Engineering Academic Project
Date: 2024
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class RouteEntry:
    """Represents a single entry in the routing table."""
    destination: str
    next_hop: str
    cost: float

    def to_dict(self) -> dict:
        return {
            "destination": self.destination,
            "next_hop": self.next_hop,
            "cost": self.cost
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'RouteEntry':
        return cls(
            destination=data["destination"],
            next_hop=data["next_hop"],
            cost=float(data["cost"])
        )


class RoutingTable:
    """Manages routing table for a router node."""

    def __init__(self, router_id: str):
        self.router_id = router_id
        self.routes: Dict[str, RouteEntry] = {}
        self.last_update_time: Optional[float] = None

    def update_table(self, routing_table_data: List[dict]) -> bool:
        """Update routing table with new data from controller (FR-06)."""
        try:
            new_routes = {}

            for entry_data in routing_table_data:
                route = RouteEntry.from_dict(entry_data)
                new_routes[route.destination] = route

            self.routes = new_routes
            import time
            self.last_update_time = time.time()

            return True

        except Exception as e:
            print(f"Error updating routing table: {e}")
            return False

    def get_route(self, destination: str) -> Optional[RouteEntry]:
        return self.routes.get(destination)

    def get_next_hop(self, destination: str) -> Optional[str]:
        route = self.routes.get(destination)
        return route.next_hop if route else None

    def get_entry_count(self) -> int:
        return len(self.routes)

    def display_table(self) -> str:
        """Display routing table in formatted output (FR-07)."""
        if not self.routes:
            return f"\nRouting Table for {self.router_id}:\n  (Empty - no routes available)\n"

        lines = [
            f"\nRouting Table for {self.router_id}:",
            "=" * 60,
            f"{'Destination':<15} {'Next Hop':<15} {'Cost':<10}",
            "=" * 60
        ]

        for destination in sorted(self.routes.keys()):
            route = self.routes[destination]
            lines.append(f"{destination:<15} {route.next_hop:<15} {route.cost:<10.1f}")

        lines.append("=" * 60)

        if self.last_update_time:
            import time
            update_time_str = time.strftime('%Y-%m-%d %H:%M:%S',
                                            time.localtime(self.last_update_time))
            lines.append(f"Last update: {update_time_str}")

        lines.append(f"Total routes: {len(self.routes)}")

        return "\n".join(lines)

    def print_table(self):
        """Print routing table to console."""
        print(self.display_table())