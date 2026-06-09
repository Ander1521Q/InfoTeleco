"""
Routing Manager for the Centralized Routing System.
Coordinates route computation and routing table distribution.
Author: Telecom Engineering Academic Project
Date: 2024
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional, Any
import socket
import time
from controller.topology_manager import TopologyManager
from controller.dijkstra import DijkstraCalculator
from common.logger import RoutingLogger
from common.messages import MessageFactory


class RoutingManager:
    """Manages route computation and routing table distribution."""

    def __init__(self, topology_manager: TopologyManager):
        self.topology_manager = topology_manager
        self.dijkstra = DijkstraCalculator()
        self.logger = RoutingLogger("RoutingManager")
        self.routing_tables: Dict[str, List[Dict]] = {}
        self.last_computation_time: Optional[float] = None

    def compute_all_routing_tables(self) -> Dict[str, List[Dict]]:
        """Compute routing tables for all routers (FR-04, FR-05)."""
        self.logger.info("Starting routing table computation for all routers")

        topology = self.topology_manager.get_topology()

        if not self.dijkstra.validate_topology(topology):
            self.logger.warning("Topology validation failed - cannot compute routes")
            return {}

        start_time = time.time()
        routing_tables = self.dijkstra.compute_routing_tables(topology)
        self.last_computation_time = time.time() - start_time

        stats = self.dijkstra.get_topology_statistics(topology)
        self.logger.info(f"Computed routing tables for {stats['router_count']} routers")
        self.logger.log_dijkstra_execution("ALL_ROUTERS", stats['router_count'])

        self.routing_tables = routing_tables
        return routing_tables

    def get_routing_table(self, router_id: str) -> List[Dict]:
        """Get routing table for specific router."""
        if not self.routing_tables:
            self.compute_all_routing_tables()

        return self.routing_tables.get(router_id, [])

    def get_routing_table_as_message(self, router_id: str) -> Optional[str]:
        """Get routing table as JSON message (FR-06)."""
        routing_table = self.get_routing_table(router_id)

        if routing_table is not None:
            return MessageFactory.create_routing_table(router_id, routing_table)

        return None

    def send_routing_table_to_router(self, router_id: str,
                                     router_ip: str,
                                     router_port: int) -> bool:
        """Send routing table to specific router over TCP (FR-06)."""
        try:
            message = self.get_routing_table_as_message(router_id)

            if not message:
                self.logger.error(f"Failed to generate routing table for {router_id}")
                return False

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)

            try:
                sock.connect((router_ip, router_port))
                sock.sendall(message.encode('utf-8'))

                response = sock.recv(4096).decode('utf-8')
                self.logger.debug(f"Received response from {router_id}: {response}")

                table_size = len(self.routing_tables.get(router_id, []))
                self.logger.log_routing_table_delivery(router_id, table_size)

                sock.close()
                return True

            except socket.timeout:
                self.logger.error(f"Timeout sending routing table to {router_id}")
                return False
            except socket.error as e:
                self.logger.error(f"Socket error sending to {router_id}: {e}")
                return False
            finally:
                sock.close()

        except Exception as e:
            self.logger.error(f"Unexpected error sending routing table to {router_id}: {e}")
            return False

    def broadcast_routing_tables(self) -> Dict[str, bool]:
        """Send routing tables to all registered routers."""
        if not self.routing_tables:
            self.compute_all_routing_tables()

        results = {}
        routers = self.topology_manager.get_all_routers()

        for router_id in routers:
            router_info = self.topology_manager.get_router(router_id)
            if router_info:
                success = self.send_routing_table_to_router(
                    router_id, router_info.ip, router_info.port
                )
                results[router_id] = success

        return results

    def update_link_cost_and_recompute(self, router1: str,
                                       router2: str,
                                       new_cost: float) -> bool:
        """Update link cost and recompute all routing tables (FR-08)."""
        topology = self.topology_manager.get_topology()
        old_cost = topology.get(router1, {}).get(router2, None)

        if old_cost is None:
            self.logger.warning(f"Link {router1}-{router2} not found in topology")
            return False

        success = self.topology_manager.update_link_cost(router1, router2, new_cost)

        if not success:
            self.logger.error(f"Failed to update link cost")
            return False

        self.logger.log_link_cost_update(router1, router2, old_cost, new_cost)

        self.routing_tables = self.compute_all_routing_tables()
        self.broadcast_routing_tables()

        return True

    def refresh_all_routing_tables(self) -> bool:
        """Force refresh of all routing tables."""
        self.logger.info("Forcing refresh of all routing tables")

        self.routing_tables = self.compute_all_routing_tables()
        results = self.broadcast_routing_tables()

        all_successful = all(results.values())

        if all_successful:
            self.logger.info("All routing tables refreshed successfully")
        else:
            failed = [rid for rid, success in results.items() if not success]
            self.logger.warning(f"Failed to refresh tables for routers: {failed}")

        return all_successful

    def get_performance_metrics(self) -> Dict:
        """Get performance metrics about routing computations."""
        topology = self.topology_manager.get_topology()
        stats = self.dijkstra.get_topology_statistics(topology)

        metrics = {
            "last_computation_time": self.last_computation_time,
            "topology_statistics": stats,
            "routing_tables_count": len(self.routing_tables),
            "total_route_entries": sum(len(table) for table in self.routing_tables.values())
        }

        return metrics