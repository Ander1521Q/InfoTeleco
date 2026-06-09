"""
Message handling module for Centralized Routing System.
Defines all JSON message structures and validation utilities.
"""

import json
from typing import Dict, List, Any, Optional
import logging


class MessageType:
    """Constants for message types used in the system."""
    REGISTER_ROUTER = "REGISTER_ROUTER"
    TOPOLOGY_UPDATE = "TOPOLOGY_UPDATE"
    ROUTING_TABLE = "ROUTING_TABLE"
    LINK_COST_UPDATE = "LINK_COST_UPDATE"
    ACKNOWLEDGMENT = "ACKNOWLEDGMENT"
    ERROR = "ERROR"


class MessageValidator:
    """Validates JSON messages according to protocol specifications."""

    @staticmethod
    def validate_register_router(message: Dict[str, Any]) -> bool:
        """
        Validate REGISTER_ROUTER message.

        Expected format:
        {
            "type": "REGISTER_ROUTER",
            "router_id": "R1",
            "ip": "127.0.0.1",
            "port": 5001
        }
        """
        required_fields = ["type", "router_id", "ip", "port"]

        for field in required_fields:
            if field not in message:
                return False

        if message["type"] != MessageType.REGISTER_ROUTER:
            return False

        if not message["router_id"].startswith("R") or not message["router_id"][1:].isdigit():
            # También aceptar TEST para pruebas
            if message["router_id"] != "TEST":
                return False

        if not isinstance(message["port"], int):
            return False

        # Permitir puertos entre 1 y 65535 (incluyendo puertos privilegiados)
        if message["port"] < 1 or message["port"] > 65535:
            return False

        return True

    @staticmethod
    def validate_topology_update(message: Dict[str, Any]) -> bool:
        """
        Validate TOPOLOGY_UPDATE message.

        Expected format:
        {
            "type": "TOPOLOGY_UPDATE",
            "router_id": "R1",
            "neighbors": [
                {"neighbor_id": "R2", "cost": 10}
            ]
        }
        """
        required_fields = ["type", "router_id", "neighbors"]

        for field in required_fields:
            if field not in message:
                return False

        if message["type"] != MessageType.TOPOLOGY_UPDATE:
            return False

        if not isinstance(message["neighbors"], list):
            return False

        for neighbor in message["neighbors"]:
            if "neighbor_id" not in neighbor or "cost" not in neighbor:
                return False
            if not isinstance(neighbor["cost"], (int, float)):
                return False
            if neighbor["cost"] < 0:
                return False

        return True

    @staticmethod
    def validate_routing_table(message: Dict[str, Any]) -> bool:
        """
        Validate ROUTING_TABLE message.

        Expected format:
        {
            "type": "ROUTING_TABLE",
            "router_id": "R1",
            "routing_table": [
                {"destination": "R2", "next_hop": "R2", "cost": 2}
            ]
        }
        """
        required_fields = ["type", "router_id", "routing_table"]

        for field in required_fields:
            if field not in message:
                return False

        if message["type"] != MessageType.ROUTING_TABLE:
            return False

        if not isinstance(message["routing_table"], list):
            return False

        for entry in message["routing_table"]:
            if "destination" not in entry or "next_hop" not in entry or "cost" not in entry:
                return False
            if not isinstance(entry["cost"], (int, float)):
                return False

        return True

    @staticmethod
    def validate_link_cost_update(message: Dict[str, Any]) -> bool:
        """Validate LINK_COST_UPDATE message."""
        required_fields = ["type", "router1", "router2", "new_cost"]

        for field in required_fields:
            if field not in message:
                return False

        if message["type"] != MessageType.LINK_COST_UPDATE:
            return False

        if not isinstance(message["new_cost"], (int, float)):
            return False

        if message["new_cost"] < 0:
            return False

        return True


class MessageFactory:
    """Factory class for creating standardized JSON messages."""

    @staticmethod
    def create_register_router(router_id: str, ip: str, port: int) -> str:
        """Create REGISTER_ROUTER message."""
        message = {
            "type": MessageType.REGISTER_ROUTER,
            "router_id": router_id,
            "ip": ip,
            "port": port
        }
        return json.dumps(message)

    @staticmethod
    def create_topology_update(router_id: str, neighbors: List[Dict]) -> str:
        """Create TOPOLOGY_UPDATE message."""
        message = {
            "type": MessageType.TOPOLOGY_UPDATE,
            "router_id": router_id,
            "neighbors": neighbors
        }
        return json.dumps(message)

    @staticmethod
    def create_routing_table(router_id: str, routing_table: List[Dict]) -> str:
        """Create ROUTING_TABLE message."""
        message = {
            "type": MessageType.ROUTING_TABLE,
            "router_id": router_id,
            "routing_table": routing_table
        }
        return json.dumps(message)

    @staticmethod
    def create_acknowledgment(message_type: str, status: str, details: str = "") -> str:
        """Create ACKNOWLEDGMENT message."""
        message = {
            "type": MessageType.ACKNOWLEDGMENT,
            "original_type": message_type,
            "status": status,
            "details": details
        }
        return json.dumps(message)

    @staticmethod
    def create_error(error_message: str, error_code: int) -> str:
        """Create ERROR message."""
        message = {
            "type": MessageType.ERROR,
            "error_message": error_message,
            "error_code": error_code
        }
        return json.dumps(message)

    @staticmethod
    def parse_message(message_str: str) -> Dict[str, Any]:
        """Parse JSON message string to dictionary."""
        try:
            return json.loads(message_str)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON message: {e}")
            raise

    @staticmethod
    def get_message_type(message_str: str) -> Optional[str]:
        """Extract message type from JSON string."""
        try:
            message = json.loads(message_str)
            return message.get("type")
        except json.JSONDecodeError:
            return None