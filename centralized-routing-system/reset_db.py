# reset_db.py - Limpia y recrea la base de datos
import mysql.connector

print("Reseteando base de datos...")

try:
    conn = mysql.connector.connect(host='localhost', user='root', password='')
    cursor = conn.cursor()

    # Eliminar base de datos si existe
    cursor.execute("DROP DATABASE IF EXISTS routing_system")
    print("✓ Base de datos eliminada")

    # Crear base de datos nueva
    cursor.execute("CREATE DATABASE routing_system")
    print("✓ Base de datos creada")

    cursor.close()
    conn.close()

    print("\nBase de datos reseteada. Ahora ejecuta: python setup_database.py")

except Exception as e:
    print(f"Error: {e}")
    print("Asegúrate que MySQL está corriendo en XAMPP")