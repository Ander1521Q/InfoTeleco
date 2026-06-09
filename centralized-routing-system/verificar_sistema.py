"""
VERIFICACIÓN RÁPIDA DEL SISTEMA
Centralized Routing System - Telecom Engineering
"""

import sys
import os


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def check_python():
    print(f"\n{Colors.BOLD}1. Python:{Colors.END}")
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 8):
        print(f"   {Colors.GREEN}✓{Colors.END} Python {version}")
        return True
    else:
        print(f"   {Colors.RED}✗{Colors.END} Python {version} (>=3.8 requerido)")
        return False


def check_modules():
    print(f"\n{Colors.BOLD}2. Módulos:{Colors.END}")
    modules = [
        ('mysql.connector', 'mysql-connector-python'),
        ('controller.dijkstra', None),
        ('controller.database_manager', None),
        ('common.messages', None),
    ]

    all_ok = True
    for module, package in modules:
        try:
            __import__(module)
            print(f"   {Colors.GREEN}✓{Colors.END} {module}")
        except ImportError:
            if package:
                print(f"   {Colors.RED}✗{Colors.END} {module} - pip install {package}")
            else:
                print(f"   {Colors.RED}✗{Colors.END} {module} - archivo faltante")
            all_ok = False
    return all_ok


def check_files():
    print(f"\n{Colors.BOLD}3. Archivos:{Colors.END}")
    files = [
        'controller/controller.py',
        'controller/dijkstra.py',
        'controller/database_manager.py',
        'router/router.py',
        'common/messages.py',
        'menu/interactive_menu.py',
        'database/schema.sql',
    ]

    all_ok = True
    for file in files:
        if os.path.exists(file):
            print(f"   {Colors.GREEN}✓{Colors.END} {file}")
        else:
            print(f"   {Colors.RED}✗{Colors.END} {file}")
            all_ok = False
    return all_ok


def check_database():
    print(f"\n{Colors.BOLD}4. Base de datos:{Colors.END}")
    try:
        from controller.database_manager import DatabaseManager
        db = DatabaseManager()
        if db.test_connection():
            routers = db.get_routers_db()
            topology = db.get_topology_db()
            print(f"   {Colors.GREEN}✓{Colors.END} Conectado")
            print(f"   {Colors.GREEN}✓{Colors.END} {len(routers)} routers")
            print(f"   {Colors.GREEN}✓{Colors.END} {len(topology)} routers en topología")
            return True
        else:
            print(f"   {Colors.RED}✗{Colors.END} No conectado")
            return False
    except Exception as e:
        print(f"   {Colors.RED}✗{Colors.END} Error: {e}")
        return False


def main():
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}  VERIFICACIÓN DEL SISTEMA{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}")

    results = [
        ("Python", check_python()),
        ("Módulos", check_modules()),
        ("Archivos", check_files()),
        ("Base de datos", check_database()),
    ]

    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}RESUMEN{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}")

    for name, passed in results:
        icon = f"{Colors.GREEN}✓{Colors.END}" if passed else f"{Colors.RED}✗{Colors.END}"
        print(f"  {icon} {name}")

    total = sum(1 for _, p in results if p)
    if total == len(results):
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ SISTEMA LISTO{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}⚠️ Ejecuta: python setup_database.py{Colors.END}")


if __name__ == "__main__":
    main()