"""
dao/topology_dao.py
TopologyDAO: stores and retrieves the network adjacency list from MySQL.
Supports FR-02 (topology update) and FR-08 (link cost update).
"""
from utils.database_connection import DatabaseConnection


class TopologyDAO:
    def __init__(self):
        self.database = DatabaseConnection()

    # ------------------------------------------------------------------ save
    def save_topology(self, router_id: str, neighbors: list):
        """
        Replace all links for router_id with the new neighbor list.
        Also inserts the reverse direction if not already present.
        """
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()

            # Remove existing outgoing links from this router
            cur.execute("DELETE FROM topology WHERE router_id = %s", (router_id,))

            insert_q = """
                INSERT INTO topology (router_id, neighbor_id, cost)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE cost = VALUES(cost)
            """
            for nb in neighbors:
                cur.execute(insert_q, (router_id, nb["neighbor_id"], nb["cost"]))
                # Also ensure the reverse link exists so Dijkstra sees both sides
                cur.execute(insert_q, (nb["neighbor_id"], router_id, nb["cost"]))

            conn.commit()
        finally:
            cur.close()
            conn.close()

    # --------------------------------------------------------------- get all
    def get_topology(self) -> dict:
        """
        Returns the full adjacency dict:
        { router_id: [{"neighbor_id": str, "cost": float}, ...], ... }
        """
        query = "SELECT router_id, neighbor_id, cost FROM topology"
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
        finally:
            cur.close()
            conn.close()

        topology: dict = {}
        for router_id, neighbor_id, cost in rows:
            topology.setdefault(router_id, []).append({
                "neighbor_id": neighbor_id,
                "cost": float(cost)
            })
        return topology

    # -------------------------------------------------------- update one link
    def update_link_cost(self, router_id: str, neighbor_id: str, cost: float) -> bool:
        """
        Update the cost of a specific link (both directions).
        Returns True if the link existed and was updated.
        """
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE topology SET cost = %s "
                "WHERE router_id = %s AND neighbor_id = %s",
                (cost, router_id, neighbor_id)
            )
            affected = cur.rowcount
            # Update reverse direction too
            cur.execute(
                "UPDATE topology SET cost = %s "
                "WHERE router_id = %s AND neighbor_id = %s",
                (cost, neighbor_id, router_id)
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return affected > 0

    # ------------------------------------------------ delete router's links
    def delete_router_links(self, router_id: str):
        """Remove all links where router_id appears (both as source and neighbor)."""
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM topology WHERE router_id = %s OR neighbor_id = %s",
                (router_id, router_id)
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()
