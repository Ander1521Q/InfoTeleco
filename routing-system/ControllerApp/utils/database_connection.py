"""
database_connection.py
Manages MySQL connections using config/database_config.json.
"""
import json
from pathlib import Path
import mysql.connector
from mysql.connector import Error


class DatabaseConnection:
    def __init__(self, config_path: str = "config/database_config.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(
                f"Database config not found: {self.config_path}"
            )
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_connection(self):
        try:
            return mysql.connector.connect(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"]
            )
        except Error as e:
            raise ConnectionError(f"MySQL connection error: {e}")
