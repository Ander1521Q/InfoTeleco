"""service/registration_service.py — Handles REGISTER_ROUTER (FR-01)."""
from model.router import Router
from dao.router_dao import RouterDAO


class RouterRegistrationService:
    def __init__(self, router_dao: RouterDAO):
        self.router_dao = router_dao

    def register_router(self, message: dict) -> dict:
        router = Router(
            router_id=message["router_id"],
            ip=message["ip"],
            port=int(message["port"]),
            status=message.get("status", "ACTIVE")
        )
        self.router_dao.save_router(router)
        return {
            "type": "ACK",
            "message": f"Router '{router.router_id}' registered successfully",
            "router_id": router.router_id
        }
