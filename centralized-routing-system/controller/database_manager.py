"""
Database Manager for Centralized Routing System.
Handles all database operations with MySQL (XAMPP).
Author: Telecom Engineering Academic Project
Date: 2024
"""

import mysql.connector
from mysql.connector import Error
from typing import Dict, List, Optional, Any
import json
import os


class DatabaseManager:
    """Manages database connections and operations."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.connection = None
        self.config = self._load_config()
        self._initialized = True

    def _load_config(self) -> dict:
        config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'routing_system',
            'user': 'root',
            'password': '',
            'charset': 'utf8mb4',
            'autocommit': True,
            'use_pure': True
        }

        config_file = 'data/db_config.json'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception:
                pass

        return config

    def _get_connection(self):
        """Get a database connection."""
        try:
            if self.connection is None or not self.connection.is_connected():
                self.connection = mysql.connector.connect(**self.config)
            return self.connection
        except Error as e:
            print(f"Database connection error: {e}")
            return None

    def execute_query(self, query: str, params: tuple = None) -> Optional[List[dict]]:
        """Execute a SELECT query and return results."""
        conn = self._get_connection()
        if not conn:
            return None

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except Error as e:
            print(f"Query error: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def execute_update(self, query: str, params: tuple = None) -> bool:
        """Execute an UPDATE/INSERT/DELETE query."""
        conn = self._get_connection()
        if not conn:
            return False

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return True
        except Error as e:
            print(f"Update error: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def execute_many(self, query: str, params_list: List[tuple]) -> bool:
        """Execute multiple queries in batch."""
        if not params_list:
            return True

        conn = self._get_connection()
        if not conn:
            return False

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            return True
        except Error as e:
            print(f"Batch update error: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def register_router_db(self, router_id: str, ip: str, port: int) -> bool:
        query = """
            INSERT INTO routers (router_id, ip_address, port_number, is_active)
            VALUES (%s, %s, %s, TRUE)
            ON DUPLICATE KEY UPDATE
            ip_address = VALUES(ip_address),
            port_number = VALUES(port_number),
            is_active = TRUE,
            last_update = CURRENT_TIMESTAMP
        """
        return self.execute_update(query, (router_id, ip, port))

    def update_topology_db(self, router1: str, router2: str, cost: float) -> bool:
        if router1 < router2:
            query = """
                INSERT INTO topology_links (router1, router2, cost, is_active)
                VALUES (%s, %s, %s, TRUE)
                ON DUPLICATE KEY UPDATE
                cost = VALUES(cost),
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
            """
            return self.execute_update(query, (router1, router2, cost))
        else:
            query = """
                INSERT INTO topology_links (router1, router2, cost, is_active)
                VALUES (%s, %s, %s, TRUE)
                ON DUPLICATE KEY UPDATE
                cost = VALUES(cost),
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
            """
            return self.execute_update(query, (router2, router1, cost))

    def get_topology_db(self) -> Dict[str, Dict[str, float]]:
        query = """
            SELECT router1, router2, cost
            FROM topology_links
            WHERE is_active = TRUE
        """
        results = self.execute_query(query)

        topology = {}
        if results:
            for row in results:
                r1 = row['router1']
                r2 = row['router2']
                cost = float(row['cost'])

                if r1 not in topology:
                    topology[r1] = {}
                if r2 not in topology:
                    topology[r2] = {}

                topology[r1][r2] = cost
                topology[r2][r1] = cost

        return topology

    def get_routers_db(self) -> Dict[str, dict]:
        query = """
            SELECT router_id, ip_address, port_number, last_update
            FROM routers
            WHERE is_active = TRUE
        """
        results = self.execute_query(query)

        routers = {}
        if results:
            for row in results:
                routers[row['router_id']] = {
                    'ip': row['ip_address'],
                    'port': row['port_number'],
                    'last_update': row['last_update']
                }

        return routers

    def store_routing_table_db(self, router_id: str, routing_table: List[Dict]) -> bool:
        update_query = "UPDATE routing_tables SET is_current = FALSE WHERE router_id = %s"
        if not self.execute_update(update_query, (router_id,)):
            return False

        insert_query = """
            INSERT INTO routing_tables (router_id, destination, next_hop, cost, is_current)
            VALUES (%s, %s, %s, %s, TRUE)
        """

        params_list = [
            (router_id, entry['destination'], entry['next_hop'], entry['cost'])
            for entry in routing_table
        ]

        if params_list:
            return self.execute_many(insert_query, params_list)

        return True

    def log_event_db(self, event_type: str, description: str,
                     router_id: str = None, details: dict = None) -> bool:
        query = """
            INSERT INTO events_log (event_type, event_description, router_id, details)
            VALUES (%s, %s, %s, %s)
        """
        details_json = json.dumps(details) if details else None
        return self.execute_update(query, (event_type, description, router_id, details_json))

    def get_event_log_db(self, limit: int = 100) -> List[Dict]:
        query = """
            SELECT event_id, event_type, event_description, router_id, 
                   details, created_at
            FROM events_log
            ORDER BY created_at DESC
            LIMIT %s
        """
        return self.execute_query(query, (limit,)) or []

    def get_routing_table_db(self, router_id: str) -> List[Dict]:
        query = """
            SELECT destination, next_hop, cost
            FROM routing_tables
            WHERE router_id = %s AND is_current = TRUE
            ORDER BY destination
        """
        return self.execute_query(query, (router_id,)) or []

    def update_link_cost_db(self, router1: str, router2: str, new_cost: float) -> bool:
        if router1 < router2:
            query = """
                UPDATE topology_links
                SET cost = %s, updated_at = CURRENT_TIMESTAMP
                WHERE router1 = %s AND router2 = %s AND is_active = TRUE
            """
            return self.execute_update(query, (new_cost, router1, router2))
        else:
            query = """
                UPDATE topology_links
                SET cost = %s, updated_at = CURRENT_TIMESTAMP
                WHERE router1 = %s AND router2 = %s AND is_active = TRUE
            """
            return self.execute_update(query, (new_cost, router2, router1))

    def delete_router_db(self, router_id: str) -> bool:
        query = "UPDATE routers SET is_active = FALSE WHERE router_id = %s"
        return self.execute_update(query, (router_id,))

    def get_statistics_db(self) -> Dict:
        stats = {}

        result = self.execute_query("SELECT COUNT(*) as count FROM routers WHERE is_active = TRUE")
        stats['active_routers'] = result[0]['count'] if result else 0

        result = self.execute_query("SELECT COUNT(*) as count FROM topology_links WHERE is_active = TRUE")
        stats['active_links'] = result[0]['count'] if result else 0

        result = self.execute_query("SELECT COUNT(*) as count FROM routing_tables WHERE is_current = TRUE")
        stats['route_entries'] = result[0]['count'] if result else 0

        result = self.execute_query("""
            SELECT COUNT(*) as count FROM events_log 
            WHERE DATE(created_at) = CURDATE()
        """)
        stats['events_today'] = result[0]['count'] if result else 0

        return stats

    def test_connection(self) -> bool:
        try:
            conn = self._get_connection()
            if conn and conn.is_connected():
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                return True
            return False
        except:
            return False

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()


db_manager = DatabaseManager()