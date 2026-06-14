"""
service/message_service.py
MessageService: validates incoming JSON messages before processing.
Covers NFR-05 (error handling) and all FR input validations.
"""
import ipaddress
from utils.constants import MessageType


class MessageService:
    VALID_STATUSES = {"ACTIVE", "ACTIVO", "INACTIVE", "INACTIVO",
                      "MAINTENANCE", "MANTENIMIENTO", "DISCONNECTED"}

    def validate_message(self, message) -> tuple:
        if not isinstance(message, dict):
            return False, "Message must be a JSON object"
        if "type" not in message:
            return False, "Missing required field: 'type'"

        t = message["type"]
        if t == MessageType.REGISTER_ROUTER:
            return self._val_register(message)
        if t == MessageType.TOPOLOGY_UPDATE:
            return self._val_topology(message)
        if t == MessageType.LINK_COST_UPDATE:
            return self._val_link_cost(message)
        if t in (MessageType.ROUTER_DOWN, MessageType.ROUTER_UP):
            return self._val_router_state(message)
        return False, f"Unsupported message type: '{t}'"

    def _val_register(self, msg):
        for f in ["router_id", "ip", "port"]:
            if f not in msg:
                return False, f"Missing field: '{f}'"
        if not isinstance(msg["router_id"], str) or not msg["router_id"]:
            return False, "router_id must be a non-empty string"
        try:
            ipaddress.ip_address(msg["ip"])
        except ValueError:
            return False, f"Invalid IP address: '{msg['ip']}'"
        if not isinstance(msg["port"], int) or msg["port"] <= 0:
            return False, "port must be a positive integer"
        if "status" in msg:
            if msg["status"].upper() not in self.VALID_STATUSES:
                return False, f"Invalid status: '{msg['status']}'"
        return True, "Valid REGISTER_ROUTER"

    def _val_topology(self, msg):
        for f in ["router_id", "neighbors"]:
            if f not in msg:
                return False, f"Missing field: '{f}'"
        if not isinstance(msg["neighbors"], list):
            return False, "neighbors must be a list"
        for nb in msg["neighbors"]:
            if not isinstance(nb, dict):
                return False, "Each neighbor must be an object"
            if "neighbor_id" not in nb or "cost" not in nb:
                return False, "Each neighbor needs neighbor_id and cost"
            if not isinstance(nb["cost"], (int, float)) or nb["cost"] < 0:
                return False, "cost must be a non-negative number"
        return True, "Valid TOPOLOGY_UPDATE"

    def _val_link_cost(self, msg):
        for f in ["router_id", "neighbor_id", "cost"]:
            if f not in msg:
                return False, f"Missing field: '{f}'"
        if not isinstance(msg["cost"], (int, float)) or msg["cost"] < 0:
            return False, "cost must be a non-negative number"
        return True, "Valid LINK_COST_UPDATE"

    def _val_router_state(self, msg):
        if "router_id" not in msg:
            return False, "Missing field: 'router_id'"
        return True, "Valid router state message"


# --- Patch: allow ADD_ROUTER type ---
# (appended to existing MessageService class — no structural change needed,
#  ADD_ROUTER is handled by CLI only, not via TCP)
