"""
PRUEBAS DE INTEGRACIÓN DEL SISTEMA COMPLETO
Centralized Routing System - Telecom Engineering
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Colors:
    """Colores para terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(title):
    """Imprime encabezado"""
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.END}")


def print_test(name, passed, details=""):
    """Imprime resultado de prueba"""
    status = f"{Colors.GREEN}✓ PASÓ{Colors.END}" if passed else f"{Colors.RED}✗ FALLÓ{Colors.END}"
    print(f"  {status}: {name}")
    if details and not passed:
        print(f"       {Colors.YELLOW}{details}{Colors.END}")


def run_system_tests():
    """Ejecuta todas las pruebas de integración del sistema"""
    print_header("PRUEBAS DE INTEGRACIÓN DEL SISTEMA")

    passed = 0
    failed = 0
    results = []

    # Prueba 1: Importación de módulos
    print("\n--- Prueba 1: Importación de módulos ---")
    try:
        from controller.dijkstra import DijkstraCalculator
        from controller.database_manager import DatabaseManager
        from controller.topology_manager import TopologyManager
        from controller.routing_manager import RoutingManager
        from common.messages import MessageFactory, MessageValidator
        from common.logger import RoutingLogger
        from router.router import Router
        from router.routing_table import RoutingTable, RouteEntry

        print_test("Todos los módulos importan correctamente", True)
        passed += 1
        results.append(("Importación de módulos", True))
    except ImportError as e:
        print_test(f"Error importando: {e}", False)
        failed += 1
        results.append(("Importación de módulos", False))

    # Prueba 2: Conexión a base de datos
    print("\n--- Prueba 2: Conexión a base de datos ---")
    try:
        from controller.database_manager import DatabaseManager
        db = DatabaseManager()
        if db.test_connection():
            routers = db.get_routers_db()
            print_test(f"Conexión exitosa ({len(routers)} routers registrados)", True)
            passed += 1
            results.append(("Base de datos", True))
        else:
            print_test("No se pudo conectar a MySQL", False)
            failed += 1
            results.append(("Base de datos", False))
    except Exception as e:
        print_test(f"Error: {e}", False)
        failed += 1
        results.append(("Base de datos", False))

    # Prueba 3: Topología en base de datos
    print("\n--- Prueba 3: Topología almacenada ---")
    try:
        from controller.database_manager import DatabaseManager
        db = DatabaseManager()
        topology = db.get_topology_db()

        if len(topology) >= 4:
            print_test(f"Topología cargada ({len(topology)} routers)", True)
            passed += 1
            results.append(("Topología", True))
        else:
            print_test(f"Solo {len(topology)} routers (esperado 4+)", False)
            failed += 1
            results.append(("Topología", False))

        # Mostrar enlaces encontrados
        if topology:
            print(f"\n  Enlaces encontrados:")
            links = set()
            for source in topology:
                for dest, cost in topology[source].items():
                    if source < dest:
                        links.add((source, dest, cost))
            for r1, r2, cost in sorted(links):
                print(f"    {r1} <--[{cost}]--> {r2}")

    except Exception as e:
        print_test(f"Error: {e}", False)
        failed += 1
        results.append(("Topología", False))

    # Prueba 4: Algoritmo Dijkstra
    print("\n--- Prueba 4: Algoritmo Dijkstra ---")
    try:
        from controller.dijkstra import DijkstraCalculator
        from controller.database_manager import DatabaseManager

        db = DatabaseManager()
        topology = db.get_topology_db()

        if topology:
            d = DijkstraCalculator()
            tables = d.compute_routing_tables(topology)

            if len(tables) >= 4:
                print_test(f"Dijkstra calculó rutas para {len(tables)} routers", True)
                passed += 1
                results.append(("Dijkstra", True))

                # Mostrar tabla de R1
                if 'R1' in tables and tables['R1']:
                    print(f"\n  Tabla de R1:")
                    for entry in tables['R1'][:3]:  # Mostrar primeras 3
                        print(f"    {entry['destination']} -> {entry['next_hop']} (costo={entry['cost']})")
            else:
                print_test(f"Solo {len(tables)} tablas (esperado 4+)", False)
                failed += 1
                results.append(("Dijkstra", False))
        else:
            print_test("No hay topología para calcular", False)
            failed += 1
            results.append(("Dijkstra", False))

    except Exception as e:
        print_test(f"Error: {e}", False)
        failed += 1
        results.append(("Dijkstra", False))

    # Prueba 5: Mensajes JSON
    print("\n--- Prueba 5: Formato de mensajes JSON ---")
    try:
        from common.messages import MessageFactory, MessageValidator
        import json

        # Probar creación de mensaje
        msg = MessageFactory.create_register_router('R1', '127.0.0.1', 5001)
        parsed = json.loads(msg)

        # Probar validación
        is_valid = MessageValidator.validate_register_router(parsed)

        if is_valid:
            print_test("Mensajes JSON válidos", True)
            passed += 1
            results.append(("Mensajes JSON", True))
        else:
            print_test("Formato de mensaje inválido", False)
            failed += 1
            results.append(("Mensajes JSON", False))

    except Exception as e:
        print_test(f"Error: {e}", False)
        failed += 1
        results.append(("Mensajes JSON", False))

    # Prueba 6: Tabla de enrutamiento
    print("\n--- Prueba 6: Tabla de enrutamiento del router ---")
    try:
        from router.routing_table import RoutingTable, RouteEntry

        # Crear tabla de prueba
        table = RoutingTable('R1')
        test_data = [
            {'destination': 'R2', 'next_hop': 'R2', 'cost': 2},
            {'destination': 'R3', 'next_hop': 'R2', 'cost': 3},
            {'destination': 'R4', 'next_hop': 'R4', 'cost': 4}
        ]
        table.update_table(test_data)

        # Verificar funcionalidad
        has_routes = table.get_entry_count() == 3
        can_get_route = table.get_route('R2') is not None
        can_display = table.display_table() is not None

        if has_routes and can_get_route and can_display:
            print_test("Tabla de enrutamiento funcional", True)
            passed += 1
            results.append(("Routing Table", True))

            # Mostrar tabla
            print(f"\n  Tabla de ejemplo:")
            print(f"    {table.display_table()}")
        else:
            print_test("Error en tabla de enrutamiento", False)
            failed += 1
            results.append(("Routing Table", False))

    except Exception as e:
        print_test(f"Error: {e}", False)
        failed += 1
        results.append(("Routing Table", False))

    # Prueba 7: Logging
    print("\n--- Prueba 7: Sistema de logging ---")
    try:
        from common.logger import RoutingLogger
        import os

        # Crear logger de prueba
        test_logger = RoutingLogger("TestLogger")
        test_logger.info("Test log message")

        # Verificar que se creó el archivo de log
        log_exists = os.path.exists("data/logs.txt")

        if log_exists:
            print_test("Sistema de logging funcional", True)
            passed += 1
            results.append(("Logging", True))
        else:
            print_test("No se pudo crear archivo de log", False)
            failed += 1
            results.append(("Logging", False))

    except Exception as e:
        print_test(f"Error: {e}", False)
        failed += 1
        results.append(("Logging", False))

    # Resumen final
    print_header("RESULTADO DE PRUEBAS DEL SISTEMA")

    for name, success in results:
        icon = f"{Colors.GREEN}✓{Colors.END}" if success else f"{Colors.RED}✗{Colors.END}"
        print(f"  {icon} {name}")

    print(f"\n{Colors.BOLD}Pruebas pasadas: {Colors.GREEN}{passed}{Colors.END}")
    print(f"{Colors.BOLD}Pruebas fallidas: {Colors.RED}{failed}{Colors.END}")
    print(f"{Colors.BOLD}Total: {passed + failed}{Colors.END}")

    porcentaje = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0
    print(f"{Colors.BOLD}Puntaje: {porcentaje:.1f}%{Colors.END}")

    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ¡SISTEMA COMPLETAMENTE FUNCIONAL!{Colors.END}")
        return True
    else:
        print(f"\n{Colors.YELLOW}⚠️ Algunas pruebas fallaron.{Colors.END}")
        print(f"\n{Colors.YELLOW}Recomendaciones:{Colors.END}")
        print(f"  1. Asegúrate que XAMPP MySQL está corriendo")
        print(f"  2. Ejecuta: python setup_database.py")
        print(f"  3. Carga la topología demo en el menú (Opción 3 -> 2)")
        return False


if __name__ == "__main__":
    success = run_system_tests()
    sys.exit(0 if success else 1)