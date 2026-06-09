"""
Tests module for Centralized Routing System
Telecom Engineering Academic Project

This module contains all test suites for the Centralized Routing System:
- test_dijkstra.py: Unit tests for Dijkstra algorithm
- test_sistema.py: Integration tests for the complete system
- test_cases.md: Manual test cases documentation

Usage:
    Run all tests: python -m tests.test_dijkstra
    Or from menu: Interactive Menu -> Test & Debug
"""

__version__ = "1.0.0"
__author__ = "Telecom Engineering"
__all__ = ["run_dijkstra_tests", "run_system_tests", "run_all_tests"]


def run_dijkstra_tests():
    """
    Run Dijkstra algorithm tests.

    Returns:
        bool: True if all tests pass, False otherwise
    """
    try:
        from tests.test_dijkstra import run_dijkstra_tests as _run_dijkstra
        return _run_dijkstra()
    except ImportError as e:
        print(f"Error importing test_dijkstra: {e}")
        return False


def run_system_tests():
    """
    Run system integration tests.

    Returns:
        bool: True if all tests pass, False otherwise
    """
    try:
        from tests.test_sistema import run_system_tests as _run_system
        return _run_system()
    except ImportError as e:
        print(f"Error importing test_sistema: {e}")
        return False


def run_all_tests():
    """
    Run all test suites and return overall result.

    Returns:
        bool: True if all tests pass, False otherwise
    """
    print("\n" + "=" * 70)
    print("  RUNNING ALL SYSTEM TESTS")
    print("=" * 70)

    results = []

    # Run Dijkstra tests
    print("\n>>> Running Dijkstra Algorithm Tests...")
    try:
        dijkstra_result = run_dijkstra_tests()
        results.append(("Dijkstra Algorithm", dijkstra_result))
    except Exception as e:
        print(f"  ✗ Error running Dijkstra tests: {e}")
        results.append(("Dijkstra Algorithm", False))

    # Run System integration tests
    print("\n>>> Running System Integration Tests...")
    try:
        system_result = run_system_tests()
        results.append(("System Integration", system_result))
    except Exception as e:
        print(f"  ✗ Error running System tests: {e}")
        results.append(("System Integration", False))

    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} test suites passed")
    print("=" * 70)

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is ready to use.")
    else:
        print("\n⚠️ Some tests failed. Check configuration and try again.")

    return passed == total


def get_test_info():
    """
    Get information about available tests.

    Returns:
        dict: Test information
    """
    return {
        "name": "Centralized Routing System Tests",
        "version": __version__,
        "author": __author__,
        "tests": [
            {"name": "Dijkstra Algorithm", "function": "run_dijkstra_tests"},
            {"name": "System Integration", "function": "run_system_tests"},
            {"name": "All Tests", "function": "run_all_tests"}
        ]
    }


if __name__ == "__main__":
    # Run all tests when module is executed directly
    import sys

    success = run_all_tests()
    sys.exit(0 if success else 1)