"""
Dijkstra's Shortest Path Algorithm implementation for the Routing System.
Computes optimal routes between routers based on link costs.
Author: Telecom Engineering Academic Project
Date: 2024
"""

import heapq
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass


@dataclass
class PathResult:
    """Represents the result of a path computation."""
    destination: str
    next_hop: str
    total_cost: float
    full_path: List[str]

    def to_dict(self) -> dict:
        return {
            "destination": self.destination,
            "next_hop": self.next_hop,
            "cost": self.total_cost
        }


class DijkstraCalculator:
    """Implements Dijkstra's algorithm for shortest path computation."""

    def __init__(self):
        self.infinity = float('inf')

    def compute_routes(self, topology: Dict[str, Dict[str, float]],
                       source_router: str) -> Dict[str, PathResult]:
        """Compute shortest paths from source router to all other routers."""

        if source_router not in topology:
            return {}

        routers = self._get_all_routers(topology)

        distances = {router: self.infinity for router in routers}
        predecessors = {router: None for router in routers}
        distances[source_router] = 0

        priority_queue = [(0, source_router)]
        visited: Set[str] = set()

        while priority_queue:
            current_distance, current_router = heapq.heappop(priority_queue)

            if current_router in visited:
                continue

            if current_distance > distances[current_router]:
                continue

            visited.add(current_router)

            neighbors = topology.get(current_router, {})
            for neighbor, edge_cost in neighbors.items():
                if neighbor in visited:
                    continue

                new_distance = current_distance + edge_cost

                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    predecessors[neighbor] = current_router
                    heapq.heappush(priority_queue, (new_distance, neighbor))

        results = {}
        for destination in routers:
            if destination == source_router:
                results[destination] = PathResult(
                    destination=destination,
                    next_hop=destination,
                    total_cost=0,
                    full_path=[destination]
                )
            elif distances[destination] != self.infinity:
                full_path = self._reconstruct_path(predecessors, source_router, destination)
                next_hop = full_path[1] if len(full_path) > 1 else destination

                results[destination] = PathResult(
                    destination=destination,
                    next_hop=next_hop,
                    total_cost=distances[destination],
                    full_path=full_path
                )
            else:
                results[destination] = PathResult(
                    destination=destination,
                    next_hop="UNREACHABLE",
                    total_cost=self.infinity,
                    full_path=[]
                )

        return results

    def compute_routing_tables(self, topology: Dict[str, Dict[str, float]]) -> Dict[str, List[Dict]]:
        """Compute routing tables for all routers in the network."""
        all_routes = {}
        routers = self._get_all_routers(topology)

        for source in routers:
            all_routes[source] = self.compute_routes(topology, source)

        routing_tables = {}

        for router_id, routes in all_routes.items():
            routing_table = []
            for destination, path_result in routes.items():
                if destination != router_id and path_result.total_cost != self.infinity:
                    routing_table.append(path_result.to_dict())

            routing_table.sort(key=lambda x: x['destination'])
            routing_tables[router_id] = routing_table

        return routing_tables

    def compute_shortest_path(self, topology: Dict[str, Dict[str, float]],
                              source: str, destination: str) -> Optional[PathResult]:
        """Compute shortest path between specific source and destination."""
        if source not in topology or destination not in topology:
            return None

        results = self.compute_routes(topology, source)
        return results.get(destination)

    def _reconstruct_path(self, predecessors: Dict[str, Optional[str]],
                          source: str, destination: str) -> List[str]:
        """Reconstruct the shortest path from source to destination."""
        path = []
        current = destination

        while current is not None:
            path.insert(0, current)
            current = predecessors[current]

        if path and path[0] != source:
            return []

        return path

    def _get_all_routers(self, topology: Dict[str, Dict[str, float]]) -> List[str]:
        """Get all router IDs from topology."""
        routers = set(topology.keys())

        for neighbors in topology.values():
            routers.update(neighbors.keys())

        return sorted(list(routers))

    def validate_topology(self, topology: Dict[str, Dict[str, float]]) -> bool:
        """Validate topology for Dijkstra execution."""
        if not topology:
            return False

        for source, neighbors in topology.items():
            for cost in neighbors.values():
                if cost < 0:
                    return False

        return True

    def get_topology_statistics(self, topology: Dict[str, Dict[str, float]]) -> Dict:
        """Calculate statistics about the topology."""
        routers = self._get_all_routers(topology)
        edge_count = sum(len(neighbors) for neighbors in topology.values())

        avg_degree = edge_count / len(routers) if routers else 0

        if routers:
            results = self.compute_routes(topology, routers[0])
            unreachable = sum(1 for r in results.values() if r.total_cost == self.infinity)
            is_connected = unreachable == 0
        else:
            is_connected = False

        return {
            "router_count": len(routers),
            "edge_count": edge_count,
            "average_degree": avg_degree,
            "is_connected": is_connected
        }