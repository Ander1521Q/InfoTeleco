"""
PRUEBAS DEL ALGORITMO DIJKSTRA
Centralized Routing System - Telecom Engineering
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controller.dijkstra import DijkstraCalculator


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


def run_dijkstra_tests():
    """Ejecuta todas las pruebas de Dijkstra"""
    print_header("PRUEBAS DEL ALGORITMO DIJKSTRA")

    passed = 0
    failed = 0
    d = DijkstraCalculator()

    # Prueba 1: Topología básica 2 routers
    print("\n--- Prueba 1: Topología básica (2 routers) ---")
    topo1 = {'R1': {'R2': 5}, 'R2': {'R1': 5}}
    r1 = d.compute_routes(topo1, 'R1')
    ok1 = 'R2' in r1 and r1['R2'].total_cost == 5
    print_test("R1 -> R2 costo 5", ok1)
    passed += 1 if ok1 else 0
    failed += 0 if ok1 else 1

    # Prueba 2: Ruta indirecta más corta
    print("\n--- Prueba 2: Ruta indirecta más corta ---")
    topo2 = {
        'R1': {'R2': 2, 'R3': 10},
        'R2': {'R1': 2, 'R3': 1},
        'R3': {'R1': 10, 'R2': 1}
    }
    r2 = d.compute_routes(topo2, 'R1')
    ok2 = r2['R3'].total_cost == 3 and r2['R3'].full_path == ['R1', 'R2', 'R3']
    print_test("R1 -> R3 debe ser 3 (vía R2)", ok2)
    passed += 1 if ok2 else 0
    failed += 0 if ok2 else 1

    # Prueba 3: Topología de demostración (4 routers)
    print("\n--- Prueba 3: Topología de demostración (4 routers) ---")
    topo3 = {
        'R1': {'R2': 2, 'R3': 5, 'R4': 4},
        'R2': {'R1': 2, 'R3': 1},
        'R3': {'R1': 5, 'R2': 1, 'R4': 3},
        'R4': {'R1': 4, 'R3': 3}
    }
    r3 = d.compute_routes(topo3, 'R1')

    ok3a = r3['R3'].total_cost == 3 and r3['R3'].full_path == ['R1', 'R2', 'R3']
    ok3b = r3['R4'].total_cost == 4 and r3['R4'].full_path == ['R1', 'R4']

    print_test("R1 -> R3 costo 3 (vía R2)", ok3a)
    print_test("R1 -> R4 costo 4 (directo)", ok3b)
    passed += (1 if ok3a else 0) + (1 if ok3b else 0)
    failed += (0 if ok3a else 1) + (0 if ok3b else 1)

    # Prueba 4: Generación de tablas de enrutamiento
    print("\n--- Prueba 4: Generación de tablas de enrutamiento ---")
    tables = d.compute_routing_tables(topo3)
    ok4 = len(tables) == 4
    print_test(f"Tablas generadas para {len(tables)} routers (esperado 4)", ok4)
    passed += 1 if ok4 else 0
    failed += 0 if ok4 else 1

    # Mostrar tabla de R1 si existe
    if 'R1' in tables:
        print(f"\n  Tabla de R1:")
        for entry in tables['R1']:
            print(f"    {entry['destination']} -> {entry['next_hop']} (costo={entry['cost']})")

    # Prueba 5: Rechazar costos negativos
    print("\n--- Prueba 5: Rechazar costos negativos ---")
    topo5 = {'R1': {'R2': -1}, 'R2': {'R1': -1}}
    ok5 = not d.validate_topology(topo5)
    print_test("Debe rechazar topología con costos negativos", ok5)
    passed += 1 if ok5 else 0
    failed += 0 if ok5 else 1

    # Prueba 6: Topología vacía
    print("\n--- Prueba 6: Topología vacía ---")
    r6 = d.compute_routes({}, 'R1')
    ok6 = r6 == {}
    print_test("Topología vacía debe retornar dict vacío", ok6)
    passed += 1 if ok6 else 0
    failed += 0 if ok6 else 1

    # Prueba 7: Nodo inalcanzable
    print("\n--- Prueba 7: Nodo inalcanzable ---")
    topo7 = {'R1': {'R2': 1}, 'R2': {'R1': 1}, 'R3': {}}
    r7 = d.compute_routes(topo7, 'R1')
    ok7 = r7['R3'].total_cost == float('inf') and r7['R3'].next_hop == 'UNREACHABLE'
    print_test("R3 debe ser UNREACHABLE", ok7)
    passed += 1 if ok7 else 0
    failed += 0 if ok7 else 1

    # Prueba 8: Estadísticas de topología
    print("\n--- Prueba 8: Estadísticas de topología ---")
    stats = d.get_topology_statistics(topo3)
    ok8 = stats.get('router_count') == 4 and stats.get('is_connected') == True
    print_test(f"Estadísticas correctas (4 routers, conectado={stats.get('is_connected')})", ok8)
    passed += 1 if ok8 else 0
    failed += 0 if ok8 else 1

    # Prueba 9: Camino específico R1->R4
    print("\n--- Prueba 9: Camino específico R1->R4 ---")
    path = d.compute_shortest_path(topo3, 'R1', 'R4')
    ok9 = path is not None and path.total_cost == 4 and path.full_path == ['R1', 'R4']
    print_test(f"R1 -> R4 costo {path.total_cost if path else 'None'} (esperado 4)", ok9)
    passed += 1 if ok9 else 0
    failed += 0 if ok9 else 1

    # Prueba 10: Rendimiento (10 routers)
    print("\n--- Prueba 10: Rendimiento (10 routers) ---")
    topo10 = {}
    for i in range(1, 11):
        topo10[f'R{i}'] = {}
        if i > 1:
            topo10[f'R{i}'][f'R{i - 1}'] = 1
        if i < 10:
            topo10[f'R{i}'][f'R{i + 1}'] = 1

    start = time.time()
    d.compute_routes(topo10, 'R1')
    elapsed_ms = (time.time() - start) * 1000
    ok10 = elapsed_ms < 10
    print_test(f"Tiempo de cómputo: {elapsed_ms:.2f}ms (<10ms)", ok10)
    passed += 1 if ok10 else 0
    failed += 0 if ok10 else 1

    # Prueba 11: Topología grande (6 routers)
    print("\n--- Prueba 11: Topología de 6 routers ---")
    topo11 = {
        'R1': {'R2': 2, 'R3': 4},
        'R2': {'R1': 2, 'R3': 1, 'R4': 3},
        'R3': {'R1': 4, 'R2': 1, 'R4': 2, 'R5': 5},
        'R4': {'R2': 3, 'R3': 2, 'R5': 1, 'R6': 3},
        'R5': {'R3': 5, 'R4': 1, 'R6': 2},
        'R6': {'R4': 3, 'R5': 2}
    }
    r11 = d.compute_routes(topo11, 'R1')
    ok11 = r11['R6'].total_cost == 8
    print_test(f"R1 -> R6 costo {r11['R6'].total_cost} (esperado 8)", ok11)
    passed += 1 if ok11 else 0
    failed += 0 if ok11 else 1

    # Resumen final
    print_header("RESULTADO DE PRUEBAS DIJKSTRA")
    print(f"\n  {Colors.BOLD}Pruebas pasadas: {Colors.GREEN}{passed}{Colors.END}")
    print(f"  {Colors.BOLD}Pruebas fallidas: {Colors.RED}{failed}{Colors.END}")
    print(f"  {Colors.BOLD}Total: {passed + failed}{Colors.END}")

    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ¡TODAS LAS PRUEBAS DE DIJKSTRA PASARON!{Colors.END}")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ {failed} pruebas fallaron{Colors.END}")
        return False


if __name__ == "__main__":
    success = run_dijkstra_tests()
    sys.exit(0 if success else 1)