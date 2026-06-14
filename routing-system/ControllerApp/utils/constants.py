"""constants.py — Message type constants."""


class MessageType:
    REGISTER_ROUTER  = "REGISTER_ROUTER"
    TOPOLOGY_UPDATE  = "TOPOLOGY_UPDATE"
    ROUTING_TABLE    = "ROUTING_TABLE"
    LINK_COST_UPDATE = "LINK_COST_UPDATE"
    ROUTER_DOWN      = "ROUTER_DOWN"
    ROUTER_UP        = "ROUTER_UP"
    ACK              = "ACK"
    ERROR            = "ERROR"
