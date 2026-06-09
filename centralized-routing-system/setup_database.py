# setup_database.py (VERSIÓN CORREGIDA)
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

    print("\n[1/3] Verificando MySQL...")
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        print("  ✓ MySQL está corriendo")
    except Error as e:
        print(f"  ✗ Error: {e}")
        return False

    print("\n[2/3] Configurando base de datos...")
    try:
        cursor.execute("CREATE DATABASE IF NOT EXISTS routing_system")
        cursor.execute("USE routing_system")
        print("  ✓ Base de datos lista")
    except Error as e:
        print(f"  ✗ Error: {e}")
        return False

    print("\n[3/3] Creando tablas...")

    # Tablas
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
    print("  ✓ Tabla 'routers'")

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
    print("  ✓ Tabla 'topology_links'")

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
    print("  ✓ Tabla 'routing_tables'")

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
    print("  ✓ Tabla 'events_log'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_configuration (
            config_key VARCHAR(50) PRIMARY KEY,
            config_value TEXT NOT NULL,
            description VARCHAR(255),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ Tabla 'system_configuration'")

    # Insertar datos demo
    print("\n  Insertando datos demo...")

    # Routers
    routers = [('R1', '127.0.0.1', 5001), ('R2', '127.0.0.1', 5002), ('R3', '127.0.0.1', 5003),
               ('R4', '127.0.0.1', 5004)]
    for r in routers:
        cursor.execute("""
            INSERT INTO routers (router_id, ip_address, port_number, is_active)
            VALUES (%s, %s, %s, TRUE)
            ON DUPLICATE KEY UPDATE
            ip_address = VALUES(ip_address),
            port_number = VALUES(port_number),
            is_active = TRUE
        """, r)
    print("  ✓ Routers demo insertados")

    # Topología
    links = [('R1', 'R2', 2), ('R1', 'R3', 5), ('R1', 'R4', 4), ('R2', 'R3', 1), ('R3', 'R4', 3)]
    for r1, r2, cost in links:
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
    print("  ✓ Topología demo insertada")

    # Configuración
    configs = [
        ('dijkstra_auto_recompute', 'true', 'Auto-recompute routes'),
        ('max_routers', '100', 'Maximum number of routers'),
        ('connection_timeout', '30', 'TCP timeout')
    ]
    for k, v, d in configs:
        cursor.execute("""
            INSERT INTO system_configuration (config_key, config_value, description)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
            config_value = VALUES(config_value)
        """, (k, v, d))
    print("  ✓ Configuración insertada")

    conn.commit()

    # Guardar configuración de conexión
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

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("  ✅ BASE DE DATOS CONFIGURADA CORRECTAMENTE")
    print("=" * 70)

    # Verificación final
    print("\nVerificando...")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from controller.database_manager import DatabaseManager
        db = DatabaseManager()
        if db.test_connection():
            stats = db.get_statistics_db()
            print(f"  ✓ Conexión exitosa")
            print(f"  ✓ Routers activos: {stats.get('active_routers', 0)}")
            print(f"  ✓ Enlaces activos: {stats.get('active_links', 0)}")
        else:
            print("  ⚠ Verificación manual requerida")
    except Exception as e:
        print(f"  ⚠ No se pudo verificar: {e}")

    return True


if __name__ == "__main__":
    setup_database()