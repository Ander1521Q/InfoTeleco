"""
dao/router_dao.py
RouterDAO: persists and retrieves Router objects from MySQL.
Supports FR-01 (registration) and the down/up CLI commands.
"""
from model.router import Router
from utils.database_connection import DatabaseConnection


class RouterDAO:
    def __init__(self):
        self.database = DatabaseConnection()

    # ------------------------------------------------------------------ save
    def save_router(self, router: Router):
        """Insert or update a router (ON DUPLICATE KEY UPDATE)."""
        query = """
            INSERT INTO routers (router_id, ip, port, status)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                ip         = VALUES(ip),
                port       = VALUES(port),
                status     = VALUES(status),
                updated_at = CURRENT_TIMESTAMP
        """
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, (router.router_id, router.ip,
                                router.port, router.status))
            conn.commit()
        finally:
            cur.close()
            conn.close()

    # --------------------------------------------------------------- get one
    def get_router_by_id(self, router_id: str):
        query = """
            SELECT router_id, ip, port, status
            FROM   routers
            WHERE  router_id = %s
        """
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, (router_id,))
            row = cur.fetchone()
        finally:
            cur.close()
            conn.close()

        if row is None:
            return None
        return Router(router_id=row[0], ip=row[1], port=row[2], status=row[3])

    # --------------------------------------------------------------- get all
    def get_all_routers(self):
        query = """
            SELECT router_id, ip, port, status
            FROM   routers
            ORDER  BY router_id
        """
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
        finally:
            cur.close()
            conn.close()

        return [Router(router_id=r[0], ip=r[1], port=r[2], status=r[3])
                for r in rows]

    # ----------------------------------------------------------------- delete
    def delete_router(self, router_id: str):
        """Remove a router and all its topology links from the DB."""
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM topology WHERE router_id = %s OR neighbor_id = %s",
                        (router_id, router_id))
            cur.execute("DELETE FROM routing_tables WHERE router_id = %s",
                        (router_id,))
            cur.execute("DELETE FROM routers WHERE router_id = %s", (router_id,))
            conn.commit()
        finally:
            cur.close()
            conn.close()

    # ---------------------------------------------------------- set status
    def set_status(self, router_id: str, status: str):
        """Change the operational status of a router."""
        conn = self.database.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE routers SET status = %s WHERE router_id = %s",
                (status, router_id)
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()
