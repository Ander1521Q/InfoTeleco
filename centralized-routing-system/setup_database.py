#!/usr/bin/env python3
"""
Setup script for Centralized Routing System database.
Run this script to initialize the database connection.
"""

import os
import sys
import json
import mysql.connector
from mysql.connector import Error


def setup_database():
    print("=" * 70)
    print("  CENTRALIZED ROUTING SYSTEM - Database Setup")
    print("=" * 70)

    config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
    }

    print("\n[1/3] Verifying MySQL...")
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        print("  ✓ MySQL is running")
    except Error as e:
        print(f"  ✗ Error: {e}")
        print("\n  Solutions:")
        print("    1. Open XAMPP Control Panel")
        print("    2. Click 'Start' next to MySQL")
        return False

    print("\n[2/3] Creating database...")
    try:
        cursor.execute("CREATE DATABASE IF NOT EXISTS routing_system")
        cursor.execute("USE routing_system")
        print("  ✓ Database 'routing_system' ready")
    except Error as e:
        print(f"  ✗ Error: {e}")
        return False

    print("\n[3/3] Creating tables...")

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routers (
            router_id VARCHAR(10) PRIMARY KEY,
            ip_address VARCHAR(45) NOT NULL,
            port_number INT NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)
    print("  ✓ Table 'routers'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topology_links (
            link_id INT AUTO_INCREMENT PRIMARY KEY,
            router1 VARCHAR(10) NOT NULL,
            router2 VARCHAR(10) NOT NULL,
            cost DECIMAL(10,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)
    print("  ✓ Table 'topology_links'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routing_tables (
            table_id INT AUTO_INCREMENT PRIMARY KEY,
            router_id VARCHAR(10) NOT NULL,
            destination VARCHAR(10) NOT NULL,
            next_hop VARCHAR(10) NOT NULL,
            cost DECIMAL(10,2) NOT NULL,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_current BOOLEAN DEFAULT TRUE
        )
    """)
    print("  ✓ Table 'routing_tables'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events_log (
            event_id INT AUTO_INCREMENT PRIMARY KEY,
            event_type VARCHAR(50) NOT NULL,
            event_description TEXT,
            router_id VARCHAR(10) NULL,
            details TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ Table 'events_log'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_configuration (
            config_key VARCHAR(50) PRIMARY KEY,
            config_value TEXT NOT NULL,
            description VARCHAR(255),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ Table 'system_configuration'")

    # Insert demo data
    print("\n  Inserting demo data...")

    # Demo routers
    demo_routers = [
        ('R1', '127.0.0.1', 5001),
        ('R2', '127.0.0.1', 5002),
        ('R3', '127.0.0.1', 5003),
        ('R4', '127.0.0.1', 5004)
    ]
    for router in demo_routers:
        cursor.execute("""
            INSERT INTO routers (router_id, ip_address, port_number, is_active)
            VALUES (%s, %s, %s, TRUE)
            ON DUPLICATE KEY UPDATE
            ip_address = VALUES(ip_address),
            port_number = VALUES(port_number),
            is_active = TRUE
        """, router)
    print("  ✓ Demo routers inserted")

    # Demo topology
    demo_links = [
        ('R1', 'R2', 2), ('R1', 'R3', 5), ('R1', 'R4', 4),
        ('R2', 'R3', 1), ('R3', 'R4', 3)
    ]
    for r1, r2, cost in demo_links:
        if r1 < r2:
            cursor.execute("""
                INSERT INTO topology_links (router1, router2, cost, is_active)
                VALUES (%s, %s, %s, TRUE)
                ON DUPLICATE KEY UPDATE
                cost = VALUES(cost),
                is_active = TRUE
            """, (r1, r2, cost))
        else:
            cursor.execute("""
                INSERT INTO topology_links (router1, router2, cost, is_active)
                VALUES (%s, %s, %s, TRUE)
                ON DUPLICATE KEY UPDATE
                cost = VALUES(cost),
                is_active = TRUE
            """, (r2, r1, cost))
    print("  ✓ Demo topology inserted")

    # System configuration
    configs = [
        ('dijkstra_auto_recompute', 'true', 'Auto-recompute routes'),
        ('max_routers', '100', 'Maximum number of routers'),
        ('connection_timeout', '30', 'TCP timeout in seconds')
    ]
    for key, value, desc in configs:
        cursor.execute("""
            INSERT INTO system_configuration (config_key, config_value, description)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
            config_value = VALUES(config_value),
            description = VALUES(description)
        """, (key, value, desc))
    print("  ✓ System configuration inserted")

    conn.commit()

    # Save connection config
    os.makedirs('data', exist_ok=True)
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'routing_system',
        'user': 'root',
        'password': ''
    }
    with open('data/db_config.json', 'w') as f:
        json.dump(db_config, f, indent=2)
    print("  ✓ Database config saved")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("  ✅ DATABASE SETUP COMPLETE!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    setup_database()