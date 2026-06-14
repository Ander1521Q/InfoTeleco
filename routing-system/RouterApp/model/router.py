"""model/router.py — Router data model for RouterApp."""
from dataclasses import dataclass, field


@dataclass
class Router:
    router_id:     str
    ip:            str
    port:          int
    status:        str
    neighbors:     list = field(default_factory=list)
    routing_table: list = field(default_factory=list)
