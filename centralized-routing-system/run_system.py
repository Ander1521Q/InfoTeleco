#!/usr/bin/env python3
"""
Main launcher for Centralized Routing System.
Author: Telecom Engineering Academic Project
Date: 2024
"""

import os
import sys
import subprocess


def show_banner():
    banner = """
    ╔══════════════════════════════════════════════════════════════════════╗
    ║     CENTRALIZED ROUTING SYSTEM - TELECOM ENGINEERING                 ║
    ║                           v1.0                                       ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_dependencies():
    try:
        import mysql.connector
        print("✓ mysql-connector-python instalado")
        return True
    except ImportError:
        print("✗ Instalando mysql-connector-python...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mysql-connector-python"])
        return True


def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    show_banner()

    print("\nVerificando dependencias...")
    check_dependencies()

    print("\n" + "=" * 50)
    print("Iniciando sistema...")
    print("=" * 50)

    try:
        from menu.interactive_menu import InteractiveMenu
        menu = InteractiveMenu()
        menu.run()
    except KeyboardInterrupt:
        print("\n\nSistema terminado.")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nEjecuta 'python setup_database.py' para configurar la base de datos.")


if __name__ == "__main__":
    main()