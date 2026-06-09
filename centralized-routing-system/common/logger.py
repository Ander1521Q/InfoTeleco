"""
Centralized logging module for the Routing System.
Provides consistent logging across controller and routers.
Author: Telecom Engineering Academic Project
Date: 2024
"""

import logging
import sys
from datetime import datetime
from typing import Optional
import os


class RoutingLogger:
    """Centralized logger for the routing system."""

    _instances = {}

    def __new__(cls, component_name: str, log_file_path: str = "data/logs.txt"):
        if component_name not in cls._instances:
            instance = super(RoutingLogger, cls).__new__(cls)
            instance._initialized = False
            cls._instances[component_name] = instance
        return cls._instances[component_name]

    def __init__(self, component_name: str, log_file_path: str = "data/logs.txt"):
        if self._initialized:
            return

        self.component_name = component_name
        self.log_file_path = log_file_path

        self.logger = logging.getLogger(component_name)
        self.logger.setLevel(logging.DEBUG)

        self.logger.handlers.clear()

        formatter = logging.Formatter(
            f'%(asctime)s - {component_name} - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        self._initialized = True

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)

    def log_registration(self, router_id: str, ip: str, port: int):
        self.info(f"REGISTRATION: Router {router_id} registered at {ip}:{port}")

    def log_topology_update(self, router_id: str, neighbors: list):
        neighbors_str = ", ".join([f"{n['neighbor_id']}(cost={n['cost']})" for n in neighbors])
        self.info(f"TOPOLOGY UPDATE: Router {router_id} reported neighbors: {neighbors_str}")

    def log_dijkstra_execution(self, source_router: str, destination_count: int):
        self.info(f"DIJKSTRA: Executed from source {source_router} to {destination_count} destinations")

    def log_routing_table_delivery(self, router_id: str, table_size: int):
        self.info(f"ROUTING TABLE: Delivered to router {router_id} with {table_size} entries")

    def log_error(self, error_message: str, error_code: int, context: Optional[dict] = None):
        context_str = f" Context: {context}" if context else ""
        self.error(f"ERROR {error_code}: {error_message}{context_str}")

    def log_connection(self, event_type: str, address: str, port: int):
        self.info(f"CONNECTION {event_type}: {address}:{port}")

    def log_link_cost_update(self, router1: str, router2: str, old_cost: float, new_cost: float):
        self.info(f"LINK UPDATE: Link {router1}-{router2} cost changed from {old_cost} to {new_cost}")