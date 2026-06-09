#!/usr/bin/env python3
"""
Main launcher for Centralized Routing System.
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
        print("✓ mysql-connector-python installed")
        return True
    except ImportError:
        print("✗ Installing mysql-connector-python...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mysql-connector-python"])
        return True


def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    show_banner()

    print("\nChecking dependencies...")
    check_dependencies()

    print("\n" + "=" * 50)
    print("Starting system...")
    print("=" * 50)

    try:
        from menu.interactive_menu import InteractiveMenu
        menu = InteractiveMenu()
        menu.run()
    except KeyboardInterrupt:
        print("\n\nSystem terminated.")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nRun 'python setup_database.py' to configure the database first.")


if __name__ == "__main__":
    main()