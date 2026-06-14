"""model/router.py — Router data model."""
from dataclasses import dataclass


@dataclass
class Router:
    router_id: str
    ip: str
    port: int
    status: str = "ACTIVE"
