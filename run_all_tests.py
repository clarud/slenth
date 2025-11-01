"""
Test suite runner for SLENTH AML System.

Runs all tests with coverage reporting and generates test report.
"""
import pytest
import sys
from pathlib import Path

# Test directories
TEST_DIRS = [
    "tests/agents/part1",
    "tests/agents/part2",
    "tests/workflows",
    "tests/services",
    "tests/crawlers",
    "tests/internal-rules",
    "tests/api"
]

def run_all_tests():
    """Run all test suites with coverage."""
    print("=" * 80)
    print("SLENTH AML SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print()
    
    # Run pytest with coverage
    args = [
        "-v",  # Verbose
        "--tb=short",  # Short traceback format
        "--cov=.",  # Coverage for all code
        "--cov-report=html",  # HTML coverage report
        "--cov-report=term-missing",  # Terminal report showing missing lines
        "--junit-xml=test-results.xml",  # JUnit XML for CI/CD
        "-ra",  # Show all test summary info
    ]
    
    # Add all test directories
    for test_dir in TEST_DIRS:
        test_path = Path(test_dir)
        if test_path.exists():
            args.append(str(test_path))
    
    # Run tests
    exit_code = pytest.main(args)
    
    print()
    print("=" * 80)
    print("Test run complete!")
    print(f"Exit code: {exit_code}")
    print("Coverage report: htmlcov/index.html")
    print("=" * 80)
    
    return exit_code


def run_specific_suite(suite_name):
    """Run specific test suite."""
    suite_map = {
        "part1": "tests/agents/part1",
        "part2": "tests/agents/part2",
        "workflows": "tests/workflows",
        "services": "tests/services",
        "crawlers": "tests/crawlers",
        "internal-rules": "tests/internal-rules",
        "api": "tests/api"
    }
    
    if suite_name not in suite_map:
        print(f"Unknown suite: {suite_name}")
        print(f"Available suites: {', '.join(suite_map.keys())}")
        return 1
    
    test_path = suite_map[suite_name]
    
    print(f"Running {suite_name} tests...")
    print("=" * 80)
    
    args = [
        "-v",
        "--tb=short",
        test_path
    ]
    
    exit_code = pytest.main(args)
    
    print()
    print(f"{suite_name} tests complete! Exit code: {exit_code}")
    
    return exit_code


def run_quick_tests():
    """Run quick smoke tests only."""
    print("Running quick smoke tests...")
    
    args = [
        "-v",
        "--tb=short",
        "-m", "not slow",  # Skip slow tests
        "-x",  # Stop on first failure
    ]
    
    for test_dir in TEST_DIRS:
        test_path = Path(test_dir)
        if test_path.exists():
            args.append(str(test_path))
    
    return pytest.main(args)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "all":
            sys.exit(run_all_tests())
        elif command == "quick":
            sys.exit(run_quick_tests())
        elif command in ["part1", "part2", "workflows", "services", "crawlers", "internal-rules", "api"]:
            sys.exit(run_specific_suite(command))
        else:
            print(f"Unknown command: {command}")
            print("Usage: python run_tests.py [all|quick|part1|part2|workflows|services|crawlers|internal-rules|api]")
            sys.exit(1)
    else:
        # Default: run all tests
        sys.exit(run_all_tests())
