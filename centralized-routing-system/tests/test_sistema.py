"""
PRUEBAS DE INTEGRACIÓN DEL SISTEMA COMPLETO
Centralized Routing System - Telecom Engineering
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(title):
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.END}")


def print_test(name, passed, details=""):
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
        from router.routing_table import RoutingTable

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
    except Exception as e:
        print_test(f"Error: {e}", False)
        failed += 1
        results.append(("Topología", False))

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