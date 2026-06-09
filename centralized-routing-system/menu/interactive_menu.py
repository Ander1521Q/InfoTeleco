"""
Interactive Menu System for Centralized Routing System.
Provides a comprehensive CLI interface for controlling and monitoring the system.
Author: Telecom Engineering Academic Project
Date: 2024
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import subprocess
from typing import Dict, Optional

from common.logger import RoutingLogger
from controller.database_manager import DatabaseManager


class Colors:
    """Colores para terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class InteractiveMenu:
    """Interactive menu system for controlling the routing system."""

    def __init__(self):
        self.db = DatabaseManager()
        self.logger = RoutingLogger("InteractiveMenu")
        self.running = True
        self.controller_process = None
        self.router_processes: Dict[str, subprocess.Popen] = {}

        self.colors = {
            'HEADER': '\033[95m',
            'BLUE': '\033[94m',
            'GREEN': '\033[92m',
            'YELLOW': '\033[93m',
            'RED': '\033[91m',
            'END': '\033[0m',
            'BOLD': '\033[1m',
        }

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        print(f"\n{self.colors['HEADER']}{'=' * 70}{self.colors['END']}")
        print(f"{self.colors['BOLD']}   CENTRALIZED ROUTING SYSTEM - TELECOM ENGINEERING{self.colors['END']}")
        print(f"{self.colors['HEADER']}{'=' * 70}{self.colors['END']}")

        if self.db.test_connection():
            print(f"   Database: {self.colors['GREEN']}Connected{self.colors['END']}")
        else:
            print(f"   Database: {self.colors['RED']}Disconnected{self.colors['END']}")

        if self.controller_process and self.controller_process.poll() is None:
            print(f"   Controller: {self.colors['GREEN']}Running{self.colors['END']}")
        else:
            print(f"   Controller: {self.colors['RED']}Stopped{self.colors['END']}")

        running = len([p for p in self.router_processes.values() if p.poll() is None])
        if running > 0:
            print(f"   Routers: {self.colors['GREEN']}{running} running{self.colors['END']}")
        else:
            print(f"   Routers: {self.colors['YELLOW']}0 running{self.colors['END']}")

        print(f"{self.colors['HEADER']}{'=' * 70}{self.colors['END']}\n")

    def print_main_menu(self):
        print(f"{self.colors['BOLD']}MAIN MENU:{self.colors['END']}")
        print(f"  {self.colors['GREEN']}1.{self.colors['END']} System Control")
        print(f"  {self.colors['GREEN']}2.{self.colors['END']} Router Management")
        print(f"  {self.colors['GREEN']}3.{self.colors['END']} Topology Management")
        print(f"  {self.colors['GREEN']}4.{self.colors['END']} Routing Tables")
        print(f"  {self.colors['GREEN']}5.{self.colors['END']} Monitoring & Logs")
        print(f"  {self.colors['GREEN']}6.{self.colors['END']} Database Management")
        print(f"  {self.colors['GREEN']}7.{self.colors['END']} Test & Debug")
        print(f"  {self.colors['RED']}0.{self.colors['END']} Exit")
        print()

    # ==================== SYSTEM CONTROL ====================

    def start_controller(self):
        if self.controller_process and self.controller_process.poll() is None:
            print(f"{self.colors['YELLOW']}Controller is already running!{self.colors['END']}")
            return

        try:
            os.makedirs('data', exist_ok=True)

            self.controller_process = subprocess.Popen(
                [sys.executable, 'controller/controller.py'],
                stdout=open('data/controller.log', 'a'),
                stderr=subprocess.STDOUT,
                text=True
            )
            time.sleep(2)

            if self.controller_process.poll() is None:
                print(f"{self.colors['GREEN']}✓ Controller started!{self.colors['END']}")
                self.db.log_event_db('CONTROLLER_START', 'Controller process started')
            else:
                print(f"{self.colors['RED']}✗ Failed to start controller{self.colors['END']}")
                self.controller_process = None
        except Exception as e:
            print(f"{self.colors['RED']}✗ Error: {e}{self.colors['END']}")

    def stop_controller(self):
        if not self.controller_process or self.controller_process.poll() is not None:
            print(f"{self.colors['YELLOW']}Controller is not running!{self.colors['END']}")
            return

        try:
            self.controller_process.terminate()
            self.controller_process.wait(timeout=5)
            print(f"{self.colors['GREEN']}✓ Controller stopped!{self.colors['END']}")
            self.db.log_event_db('CONTROLLER_STOP', 'Controller process stopped')
        except subprocess.TimeoutExpired:
            self.controller_process.kill()
            print(f"{self.colors['GREEN']}✓ Controller killed!{self.colors['END']}")
        finally:
            self.controller_process = None

    def start_router(self, router_id: str, listen_port: int = None):
        if router_id in self.router_processes:
            proc = self.router_processes[router_id]
            if proc and proc.poll() is None:
                print(f"{self.colors['YELLOW']}Router {router_id} is already running!{self.colors['END']}")
                return

        try:
            cmd = [sys.executable, 'router/router.py', router_id]
            if listen_port:
                cmd.extend(['--listen-port', str(listen_port)])

            process = subprocess.Popen(
                cmd,
                stdout=open(f'data/router_{router_id}.log', 'a'),
                stderr=subprocess.STDOUT,
                text=True
            )
            time.sleep(1)

            if process.poll() is None:
                self.router_processes[router_id] = process
                print(f"{self.colors['GREEN']}✓ Router {router_id} started!{self.colors['END']}")
                self.db.register_router_db(router_id, '127.0.0.1', listen_port or 5000 + int(router_id[1:]))
            else:
                print(f"{self.colors['RED']}✗ Failed to start router {router_id}{self.colors['END']}")
        except Exception as e:
            print(f"{self.colors['RED']}✗ Error: {e}{self.colors['END']}")

    def stop_router(self, router_id: str):
        if router_id not in self.router_processes:
            print(f"{self.colors['YELLOW']}Router {router_id} is not running!{self.colors['END']}")
            return

        try:
            process = self.router_processes[router_id]
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=3)
            print(f"{self.colors['GREEN']}✓ Router {router_id} stopped!{self.colors['END']}")
            del self.router_processes[router_id]
        except Exception as e:
            print(f"{self.colors['RED']}✗ Error: {e}{self.colors['END']}")

    def start_all_routers(self):
        ports = {'R1': 5001, 'R2': 5002, 'R3': 5003, 'R4': 5004}
        for router_id in ['R1', 'R2', 'R3', 'R4']:
            if router_id not in self.router_processes:
                self.start_router(router_id, ports[router_id])
                time.sleep(0.5)

    def stop_all_routers(self):
        for router_id in list(self.router_processes.keys()):
            self.stop_router(router_id)
            time.sleep(0.3)

    def list_routers(self):
        routers = self.db.get_routers_db()
        if not routers:
            print(f"{self.colors['YELLOW']}No routers registered.{self.colors['END']}")
            return

        print(f"\n{self.colors['BOLD']}Registered Routers:{self.colors['END']}")
        print(f"{'ID':<10} {'IP':<20} {'Port':<10} {'Status':<12}")
        print("-" * 55)

        for router_id, info in routers.items():
            proc = self.router_processes.get(router_id)
            status = "Running" if proc and proc.poll() is None else "Stopped"
            status_color = self.colors['GREEN'] if status == "Running" else self.colors['YELLOW']
            print(f"{router_id:<10} {info['ip']:<20} {info['port']:<10} {status_color}{status}{self.colors['END']}")

    # ==================== TOPOLOGY MANAGEMENT ====================

    def view_topology(self):
        topology = self.db.get_topology_db()
        if not topology:
            print(f"{self.colors['YELLOW']}No topology data available.{self.colors['END']}")
            return

        print(f"\n{self.colors['BOLD']}Network Topology:{self.colors['END']}")
        print("=" * 50)

        links = set()
        for source in topology:
            for dest, cost in topology[source].items():
                if source < dest:
                    links.add((source, dest))
                    print(f"  {source} <--[{cost}]--> {dest}")

        print(f"\n{self.colors['BOLD']}Graph Representation:{self.colors['END']}")
        for router in sorted(topology.keys()):
            neighbors = topology[router]
            neighbors_str = ", ".join([f"{n}({c})" for n, c in neighbors.items()])
            print(f"  {router}: {neighbors_str}")

    def load_demo_topology(self):
        demo_links = [
            ('R1', 'R2', 2), ('R1', 'R3', 5), ('R1', 'R4', 4),
            ('R2', 'R3', 1), ('R3', 'R4', 3)
        ]

        print(f"\n{self.colors['YELLOW']}Loading demo topology...{self.colors['END']}")

        ports = {'R1': 5001, 'R2': 5002, 'R3': 5003, 'R4': 5004}
        for router_id, port in ports.items():
            self.db.register_router_db(router_id, '127.0.0.1', port)

        for r1, r2, cost in demo_links:
            self.db.update_topology_db(r1, r2, cost)

        print(f"{self.colors['GREEN']}✓ Demo topology loaded!{self.colors['END']}")
        self.db.log_event_db('DEMO_LOADED', 'Demo topology loaded (4 routers, 5 links)')
        self.view_topology()

    def compute_routes(self):
        topology = self.db.get_topology_db()
        if not topology:
            print(f"{self.colors['RED']}No topology available!{self.colors['END']}")
            return

        from controller.dijkstra import DijkstraCalculator
        dijkstra = DijkstraCalculator()

        print(f"{self.colors['YELLOW']}Computing routes...{self.colors['END']}")
        routing_tables = dijkstra.compute_routing_tables(topology)

        for router_id, routing_table in routing_tables.items():
            self.db.store_routing_table_db(router_id, routing_table)

        print(f"{self.colors['GREEN']}✓ Routes computed for {len(routing_tables)} routers!{self.colors['END']}")
        self.db.log_event_db('ROUTE_COMPUTATION', f'Dijkstra computed for {len(routing_tables)} routers')

    def view_routing_tables(self):
        routers = self.db.get_routers_db()
        if not routers:
            print(f"{self.colors['YELLOW']}No routers registered.{self.colors['END']}")
            return

        for router_id in routers.keys():
            routing_table = self.db.get_routing_table_db(router_id)
            print(f"\n{self.colors['BOLD']}Routing Table for {router_id}:{self.colors['END']}")
            print("=" * 50)

            if routing_table:
                print(f"{'Destination':<12} {'Next Hop':<12} {'Cost':<10}")
                print("-" * 35)
                for entry in routing_table:
                    print(f"{entry['destination']:<12} {entry['next_hop']:<12} {entry['cost']:<10.1f}")
                print(f"\nTotal entries: {len(routing_table)}")
            else:
                print("  No routes available")

    def view_event_logs(self):
        events = self.db.get_event_log_db(20)
        if not events:
            print(f"{self.colors['YELLOW']}No events found.{self.colors['END']}")
            return

        print(f"\n{self.colors['BOLD']}Recent Events:{self.colors['END']}")
        print("=" * 80)
        for event in events:
            print(f"[{event['created_at']}] {event['event_type']}")
            print(f"    {event['event_description']}")
            if event['router_id']:
                print(f"    Router: {event['router_id']}")
            print()

    def test_database(self):
        print(f"\n{self.colors['BOLD']}Database Test:{self.colors['END']}")
        if self.db.test_connection():
            print(f"{self.colors['GREEN']}✓ Database connected!{self.colors['END']}")
            stats = self.db.get_statistics_db()
            print(f"  Routers: {stats.get('active_routers', 0)}")
            print(f"  Links: {stats.get('active_links', 0)}")
            print(f"  Routes: {stats.get('route_entries', 0)}")
        else:
            print(f"{self.colors['RED']}✗ Database connection failed!{self.colors['END']}")

    # ==================== TEST & DEBUG MENU ====================

    def test_submenu(self):
        """Test submenu - With all integrated tests"""
        while True:
            self.clear_screen()
            self.print_header()
            print(f"{self.colors['BOLD']}TEST & DEBUG{self.colors['END']}")
            print("  " + "-" * 40)
            print(f"  {self.colors['GREEN']}1.{self.colors['END']} Test Database Connection")
            print(f"  {self.colors['GREEN']}2.{self.colors['END']} Test Dijkstra Algorithm")
            print(f"  {self.colors['GREEN']}3.{self.colors['END']} Test System Integration")
            print(f"  {self.colors['GREEN']}4.{self.colors['END']} Test Message Validation")
            print(f"  {self.colors['GREEN']}5.{self.colors['END']} Run All Tests")
            print(f"  {self.colors['GREEN']}6.{self.colors['END']} Quick System Check")
            print(f"  {self.colors['RED']}0.{self.colors['END']} Back")
            print()

            choice = input(f"{self.colors['BOLD']}Select option: {self.colors['END']}").strip()

            if choice == '1':
                self.test_database_connection()
                input("Press Enter to continue...")
            elif choice == '2':
                self.test_dijkstra_algorithm()
                input("Press Enter to continue...")
            elif choice == '3':
                self.test_system_integration()
                input("Press Enter to continue...")
            elif choice == '4':
                self.test_message_validation()
                input("Press Enter to continue...")
            elif choice == '5':
                self.run_all_tests()
                input("Press Enter to continue...")
            elif choice == '6':
                self.quick_system_check()
                input("Press Enter to continue...")
            elif choice == '0':
                break

    def test_database_connection(self):
        """Test database connection"""
        print(f"\n{self.colors['BOLD']}=== TEST DATABASE CONNECTION ==={self.colors['END']}")

        if self.db.test_connection():
            print(f"{self.colors['GREEN']}✓ Database connected successfully!{self.colors['END']}")

            stats = self.db.get_statistics_db()
            print(f"\n{self.colors['BOLD']}Statistics:{self.colors['END']}")
            print(f"  Active Routers: {stats.get('active_routers', 0)}")
            print(f"  Active Links: {stats.get('active_links', 0)}")
            print(f"  Route Entries: {stats.get('route_entries', 0)}")
            print(f"  Events Today: {stats.get('events_today', 0)}")
        else:
            print(f"{self.colors['RED']}✗ Database connection failed!{self.colors['END']}")
            print(f"\n{self.colors['YELLOW']}Solutions:{self.colors['END']}")
            print("  1. Start XAMPP MySQL")
            print("  2. Run: python setup_database.py")

    def test_dijkstra_algorithm(self):
        """Run Dijkstra algorithm tests"""
        print(f"\n{self.colors['BOLD']}=== TEST DIJKSTRA ALGORITHM ==={self.colors['END']}")

        try:
            from controller.dijkstra import DijkstraCalculator

            d = DijkstraCalculator()
            passed = 0
            total = 0

            # Test 1: Basic topology
            print(f"\n{self.colors['BOLD']}Test 1: Basic topology (2 routers){self.colors['END']}")
            topo1 = {'R1': {'R2': 5}, 'R2': {'R1': 5}}
            r1 = d.compute_routes(topo1, 'R1')
            ok1 = 'R2' in r1 and r1['R2'].total_cost == 5
            print(f"  {'✓' if ok1 else '✗'} R1 -> R2: cost {r1['R2'].total_cost if 'R2' in r1 else 'N/A'} (expected 5)")
            passed += 1 if ok1 else 0
            total += 1

            # Test 2: Indirect path
            print(f"\n{self.colors['BOLD']}Test 2: Indirect path (3 routers){self.colors['END']}")
            topo2 = {
                'R1': {'R2': 2, 'R3': 10},
                'R2': {'R1': 2, 'R3': 1},
                'R3': {'R1': 10, 'R2': 1}
            }
            r2 = d.compute_routes(topo2, 'R1')
            ok2 = r2['R3'].total_cost == 3 and r2['R3'].full_path == ['R1', 'R2', 'R3']
            print(f"  {'✓' if ok2 else '✗'} R1 -> R3: cost {r2['R3'].total_cost} (expected 3)")
            passed += 1 if ok2 else 0
            total += 1

            # Test 3: Demo topology
            print(f"\n{self.colors['BOLD']}Test 3: Demo topology (4 routers){self.colors['END']}")
            topo3 = {
                'R1': {'R2': 2, 'R3': 5, 'R4': 4},
                'R2': {'R1': 2, 'R3': 1},
                'R3': {'R1': 5, 'R2': 1, 'R4': 3},
                'R4': {'R1': 4, 'R3': 3}
            }
            r3 = d.compute_routes(topo3, 'R1')
            ok3a = r3['R3'].total_cost == 3
            ok3b = r3['R4'].total_cost == 4
            print(f"  {'✓' if ok3a else '✗'} R1 -> R3: cost {r3['R3'].total_cost} (expected 3)")
            print(f"  {'✓' if ok3b else '✗'} R1 -> R4: cost {r3['R4'].total_cost} (expected 4)")
            passed += (1 if ok3a else 0) + (1 if ok3b else 0)
            total += 2

            # Summary
            print(f"\n{self.colors['BLUE']}{'=' * 50}{self.colors['END']}")
            print(f"{self.colors['BOLD']}RESULT: {passed}/{total} tests passed{self.colors['END']}")
            print(f"{self.colors['BLUE']}{'=' * 50}{self.colors['END']}")

            if passed == total:
                print(f"\n{self.colors['GREEN']}✓ Dijkstra algorithm is working correctly!{self.colors['END']}")
            else:
                print(f"\n{self.colors['RED']}✗ Some tests failed{self.colors['END']}")

        except Exception as e:
            print(f"{self.colors['RED']}Error: {e}{self.colors['END']}")

    def test_system_integration(self):
        """Run system integration tests"""
        print(f"\n{self.colors['BOLD']}=== TEST SYSTEM INTEGRATION ==={self.colors['END']}")

        results = []

        # Test 1: Module imports
        print(f"\n{self.colors['BOLD']}1. Module imports:{self.colors['END']}")
        try:
            from controller.dijkstra import DijkstraCalculator
            from controller.database_manager import DatabaseManager
            from common.messages import MessageFactory, MessageValidator
            from router.router import Router
            print(f"  {self.colors['GREEN']}✓ All modules imported{self.colors['END']}")
            results.append(True)
        except ImportError as e:
            print(f"  {self.colors['RED']}✗ Import error: {e}{self.colors['END']}")
            results.append(False)

        # Test 2: Database
        print(f"\n{self.colors['BOLD']}2. Database connection:{self.colors['END']}")
        if self.db.test_connection():
            routers = self.db.get_routers_db()
            print(f"  {self.colors['GREEN']}✓ Connected ({len(routers)} routers){self.colors['END']}")
            results.append(True)
        else:
            print(f"  {self.colors['RED']}✗ Not connected{self.colors['END']}")
            results.append(False)

        # Test 3: Topology
        print(f"\n{self.colors['BOLD']}3. Topology:{self.colors['END']}")
        topology = self.db.get_topology_db()
        if topology:
            print(f"  {self.colors['GREEN']}✓ Topology loaded ({len(topology)} routers){self.colors['END']}")
            results.append(True)
        else:
            print(f"  {self.colors['YELLOW']}⚠ No topology loaded{self.colors['END']}")
            results.append(False)

        # Summary
        passed = sum(results)
        total = len(results)

        print(f"\n{self.colors['BLUE']}{'=' * 50}{self.colors['END']}")
        print(f"{self.colors['BOLD']}RESULT: {passed}/{total} tests passed{self.colors['END']}")
        print(f"{self.colors['BLUE']}{'=' * 50}{self.colors['END']}")

    def test_message_validation(self):
        """Test message validation"""
        print(f"\n{self.colors['BOLD']}=== TEST MESSAGE VALIDATION ==={self.colors['END']}")

        from common.messages import MessageValidator

        test_cases = [
            ({'type': 'REGISTER_ROUTER', 'router_id': 'R1', 'ip': '127.0.0.1', 'port': 5001}, True, "Valid message"),
            ({'type': 'REGISTER_ROUTER', 'router_id': 'R1', 'ip': '127.0.0.1', 'port': -1}, False, "Invalid port"),
            ({'type': 'INVALID', 'router_id': 'R1'}, False, "Invalid type"),
            ({'type': 'REGISTER_ROUTER', 'router_id': 'R1'}, False, "Missing fields"),
        ]

        passed = 0
        for msg, expected, desc in test_cases:
            result = MessageValidator.validate_register_router(msg)
            if result == expected:
                print(f"  {self.colors['GREEN']}✓{self.colors['END']} {desc}")
                passed += 1
            else:
                print(f"  {self.colors['RED']}✗{self.colors['END']} {desc}")

        print(f"\n{self.colors['BOLD']}RESULT: {passed}/{len(test_cases)} tests passed{self.colors['END']}")

    def run_all_tests(self):
        """Run all system tests"""
        print(f"\n{self.colors['BOLD']}{'=' * 60}{self.colors['END']}")
        print(f"{self.colors['BOLD']}  RUNNING ALL SYSTEM TESTS{self.colors['END']}")
        print(f"{self.colors['BOLD']}{'=' * 60}{self.colors['END']}")

        results = []

        # Test 1: Database
        print(f"\n{self.colors['BOLD']}1. Database Test:{self.colors['END']}")
        db_ok = self.db.test_connection()
        print(f"   {'✓' if db_ok else '✗'} Database connection")
        results.append(("Database", db_ok))

        # Test 2: Dijkstra
        print(f"\n{self.colors['BOLD']}2. Dijkstra Test:{self.colors['END']}")
        try:
            from controller.dijkstra import DijkstraCalculator
            d = DijkstraCalculator()
            topo = {'R1': {'R2': 2}, 'R2': {'R1': 2}}
            r = d.compute_routes(topo, 'R1')
            dijkstra_ok = 'R2' in r
            print(f"   {'✓' if dijkstra_ok else '✗'} Dijkstra algorithm")
            results.append(("Dijkstra", dijkstra_ok))
        except Exception as e:
            print(f"   ✗ Error: {e}")
            results.append(("Dijkstra", False))

        # Test 3: Topology
        print(f"\n{self.colors['BOLD']}3. Topology Test:{self.colors['END']}")
        topology = self.db.get_topology_db()
        topo_ok = len(topology) >= 1
        print(f"   {'✓' if topo_ok else '✗'} Topology loaded ({len(topology)} routers)")
        results.append(("Topology", topo_ok))

        # Summary
        print(f"\n{self.colors['BLUE']}{'=' * 60}{self.colors['END']}")
        print(f"{self.colors['BOLD']}TEST SUMMARY{self.colors['END']}")
        print(f"{self.colors['BLUE']}{'=' * 60}{self.colors['END']}")

        passed = sum(1 for _, ok in results if ok)
        total = len(results)

        for name, ok in results:
            icon = f"{self.colors['GREEN']}✓{self.colors['END']}" if ok else f"{self.colors['RED']}✗{self.colors['END']}"
            print(f"  {icon} {name}")

        print(f"\n{self.colors['BOLD']}Total: {passed}/{total} tests passed{self.colors['END']}")

        if passed == total:
            print(f"\n{self.colors['GREEN']}🎉 ALL TESTS PASSED! System is ready.{self.colors['END']}")
        else:
            print(
                f"\n{self.colors['YELLOW']}⚠️ Some tests failed. Run 'python setup_database.py' to fix.{self.colors['END']}")

    def quick_system_check(self):
        """Quick system health check"""
        print(f"\n{self.colors['BOLD']}=== QUICK SYSTEM CHECK ==={self.colors['END']}")

        # Check Python
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        print(f"  Python: {py_version} {'✓' if sys.version_info >= (3, 8) else '⚠️'}")

        # Check Database
        db_ok = self.db.test_connection()
        print(f"  Database: {'✓ Connected' if db_ok else '✗ Disconnected'}")

        # Check Controller
        controller_running = self.controller_process and self.controller_process.poll() is None
        print(f"  Controller: {'✓ Running' if controller_running else '○ Stopped'}")

        # Check Routers
        routers_running = len([p for p in self.router_processes.values() if p.poll() is None])
        print(f"  Routers: {routers_running} running")

        # Check Topology
        topology = self.db.get_topology_db()
        link_count = sum(len(n) for n in topology.values()) // 2 if topology else 0
        print(f"  Topology: {len(topology)} routers, {link_count} links")

        # Recommendations
        print(f"\n{self.colors['BOLD']}Recommendations:{self.colors['END']}")
        if not db_ok:
            print(f"  {self.colors['YELLOW']}• Start XAMPP MySQL and run: python setup_database.py{self.colors['END']}")
        if not topology:
            print(f"  {self.colors['GREEN']}• Load demo topology (Option 3 -> 2){self.colors['END']}")
        if not controller_running and db_ok and topology:
            print(f"  {self.colors['GREEN']}• Start controller (Option 1 -> 1){self.colors['END']}")
        if routers_running == 0 and controller_running:
            print(f"  {self.colors['GREEN']}• Start routers (Option 1 -> 3){self.colors['END']}")

    # ==================== SUBMENUS ====================

    def system_control_menu(self):
        while True:
            self.clear_screen()
            self.print_header()
            print(f"{self.colors['BOLD']}SYSTEM CONTROL{self.colors['END']}")
            print("  " + "-" * 40)
            print(f"  {self.colors['GREEN']}1.{self.colors['END']} Start Controller")
            print(f"  {self.colors['GREEN']}2.{self.colors['END']} Stop Controller")
            print(f"  {self.colors['GREEN']}3.{self.colors['END']} Start All Routers")
            print(f"  {self.colors['GREEN']}4.{self.colors['END']} Stop All Routers")
            print(f"  {self.colors['GREEN']}5.{self.colors['END']} Check System Status")
            print(f"  {self.colors['RED']}0.{self.colors['END']} Back")
            print()

            choice = input(f"{self.colors['BOLD']}Select option: {self.colors['END']}").strip()

            if choice == '1':
                self.start_controller()
                input("Press Enter...")
            elif choice == '2':
                self.stop_controller()
                input("Press Enter...")
            elif choice == '3':
                self.start_all_routers()
                input("Press Enter...")
            elif choice == '4':
                self.stop_all_routers()
                input("Press Enter...")
            elif choice == '5':
                self.quick_system_check()
                input("Press Enter...")
            elif choice == '0':
                break

    def router_management_menu(self):
        while True:
            self.clear_screen()
            self.print_header()
            print(f"{self.colors['BOLD']}ROUTER MANAGEMENT{self.colors['END']}")
            print("  " + "-" * 40)
            print(f"  {self.colors['GREEN']}1.{self.colors['END']} List Routers")
            print(f"  {self.colors['GREEN']}2.{self.colors['END']} Start Router")
            print(f"  {self.colors['GREEN']}3.{self.colors['END']} Stop Router")
            print(f"  {self.colors['RED']}0.{self.colors['END']} Back")
            print()

            choice = input(f"{self.colors['BOLD']}Select option: {self.colors['END']}").strip()

            if choice == '1':
                self.list_routers()
                input("Press Enter...")
            elif choice == '2':
                rid = input("Router ID (R1-R4): ").strip().upper()
                self.start_router(rid)
                input("Press Enter...")
            elif choice == '3':
                rid = input("Router ID: ").strip().upper()
                self.stop_router(rid)
                input("Press Enter...")
            elif choice == '0':
                break

    def topology_management_menu(self):
        while True:
            self.clear_screen()
            self.print_header()
            print(f"{self.colors['BOLD']}TOPOLOGY MANAGEMENT{self.colors['END']}")
            print("  " + "-" * 40)
            print(f"  {self.colors['GREEN']}1.{self.colors['END']} View Topology")
            print(f"  {self.colors['GREEN']}2.{self.colors['END']} Load Demo Topology")
            print(f"  {self.colors['GREEN']}3.{self.colors['END']} Compute Routes")
            print(f"  {self.colors['RED']}0.{self.colors['END']} Back")
            print()

            choice = input(f"{self.colors['BOLD']}Select option: {self.colors['END']}").strip()

            if choice == '1':
                self.view_topology()
                input("Press Enter...")
            elif choice == '2':
                self.load_demo_topology()
                input("Press Enter...")
            elif choice == '3':
                self.compute_routes()
                input("Press Enter...")
            elif choice == '0':
                break

    def routing_tables_menu(self):
        while True:
            self.clear_screen()
            self.print_header()
            print(f"{self.colors['BOLD']}ROUTING TABLES{self.colors['END']}")
            print("  " + "-" * 40)
            print(f"  {self.colors['GREEN']}1.{self.colors['END']} View All Routing Tables")
            print(f"  {self.colors['RED']}0.{self.colors['END']} Back")
            print()

            choice = input(f"{self.colors['BOLD']}Select option: {self.colors['END']}").strip()

            if choice == '1':
                self.view_routing_tables()
                input("Press Enter...")
            elif choice == '0':
                break

    def monitoring_menu(self):
        while True:
            self.clear_screen()
            self.print_header()
            print(f"{self.colors['BOLD']}MONITORING & LOGS{self.colors['END']}")
            print("  " + "-" * 40)
            print(f"  {self.colors['GREEN']}1.{self.colors['END']} View Event Logs")
            print(f"  {self.colors['RED']}0.{self.colors['END']} Back")
            print()

            choice = input(f"{self.colors['BOLD']}Select option: {self.colors['END']}").strip()

            if choice == '1':
                self.view_event_logs()
                input("Press Enter...")
            elif choice == '0':
                break

    def database_menu(self):
        while True:
            self.clear_screen()
            self.print_header()
            print(f"{self.colors['BOLD']}DATABASE MANAGEMENT{self.colors['END']}")
            print("  " + "-" * 40)
            print(f"  {self.colors['GREEN']}1.{self.colors['END']} Test Connection")
            print(f"  {self.colors['GREEN']}2.{self.colors['END']} View Statistics")
            print(f"  {self.colors['RED']}0.{self.colors['END']} Back")
            print()

            choice = input(f"{self.colors['BOLD']}Select option: {self.colors['END']}").strip()

            if choice == '1':
                self.test_database()
                input("Press Enter...")
            elif choice == '2':
                stats = self.db.get_statistics_db()
                print(f"\n{self.colors['BOLD']}Database Statistics:{self.colors['END']}")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                input("Press Enter...")
            elif choice == '0':
                break

    # ==================== MAIN LOOP ====================

    def run(self):
        """Main menu loop"""
        while self.running:
            try:
                self.clear_screen()
                self.print_header()
                self.print_main_menu()

                choice = input(f"{self.colors['BOLD']}Select option: {self.colors['END']}").strip()

                if choice == '1':
                    self.system_control_menu()
                elif choice == '2':
                    self.router_management_menu()
                elif choice == '3':
                    self.topology_management_menu()
                elif choice == '4':
                    self.routing_tables_menu()
                elif choice == '5':
                    self.monitoring_menu()
                elif choice == '6':
                    self.database_menu()
                elif choice == '7':
                    self.test_submenu()
                elif choice == '0':
                    self.confirm_exit()
                else:
                    print(f"{self.colors['YELLOW']}Invalid option!{self.colors['END']}")
                    time.sleep(1)

            except KeyboardInterrupt:
                self.confirm_exit()
            except Exception as e:
                print(f"{self.colors['RED']}Error: {e}{self.colors['END']}")
                time.sleep(2)

    def confirm_exit(self):
        confirm = input(f"\n{self.colors['YELLOW']}Exit system? (y/n): {self.colors['END']}").strip().lower()
        if confirm == 'y':
            self.stop_all_routers()
            self.stop_controller()
            print(f"{self.colors['GREEN']}Goodbye!{self.colors['END']}")
            self.running = False
            sys.exit(0)


def main():
    menu = InteractiveMenu()
    try:
        menu.run()
    except KeyboardInterrupt:
        menu.confirm_exit()


if __name__ == "__main__":
    main()