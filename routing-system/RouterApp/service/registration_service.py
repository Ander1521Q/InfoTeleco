"""service/registration_service.py — Builds REGISTER_ROUTER message."""
from model.router import Router


class RegistrationService:
    @staticmethod
    def create_registration_message(router: Router) -> dict:
        return {
            "type":      "REGISTER_ROUTER",
            "router_id": router.router_id,
            "ip":        router.ip,
            "port":      router.port,
            "status":    router.status
        }
