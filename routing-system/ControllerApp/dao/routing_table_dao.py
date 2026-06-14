"""
dao/routing_table_dao.py
RoutingTableDAO: persists routing tables computed by Dijkstra.
Supports FR-05 (routing table generation) and FR-06 (delivery).
"""
from utils.database_connection import DatabaseConnection


class RoutingTableDAO:
    def __init__(self):
        self.database = DatabaseConnection()

    def save_routing_table(self, router_id: str, table: list):
        """Replace the routing table for router_id with the new entries."""
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM routing_tables WHERE router_id = %s", (router_id,)
            )
            for entry in table:
                cur.execute(
                    """
                    INSERT INTO routing_tables
                        (router_id, destination, next_hop, cost)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (router_id, entry["destination"],
                     entry["next_hop"], entry["cost"])
                )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def get_routing_table(self, router_id: str) -> list:
        """Return the stored routing table for a router."""
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT destination, next_hop, cost
                FROM   routing_tables
                WHERE  router_id = %s
                ORDER  BY destination
                """,
                (router_id,)
            )
            rows = cur.fetchall()
        finally:
            cur.close()
            conn.close()

        return [{"destination": r[0], "next_hop": r[1], "cost": float(r[2])}
                for r in rows]

    def get_all_routing_tables(self) -> dict:
        """Return all routing tables as {router_id: [entries]}."""
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT router_id, destination, next_hop, cost "
                "FROM routing_tables ORDER BY router_id, destination"
            )
            rows = cur.fetchall()
        finally:
            cur.close()
            conn.close()

        tables: dict = {}
        for router_id, dest, nh, cost in rows:
            tables.setdefault(router_id, []).append({
                "destination": dest,
                "next_hop":    nh,
                "cost":        float(cost)
            })
        return tables
