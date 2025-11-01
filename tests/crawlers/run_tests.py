"""
Test runner script for crawler tests.

Usage:
    # Run all tests
    python tests/crawlers/run_tests.py

    # Run specific test file
    python tests/crawlers/run_tests.py --file test_hkma

    # Run with verbose output
    python tests/crawlers/run_tests.py --verbose

    # Run integration tests
    python tests/crawlers/run_tests.py --integration

    # Run performance tests
    python tests/crawlers/run_tests.py --performance
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_pytest(args):
    """Run pytest with specified arguments"""
    cmd = ["pytest", "tests/crawlers/"]
    
    if args.file:
        cmd = ["pytest", f"tests/crawlers/{args.file}.py"]
    
    if args.verbose:
        cmd.append("-v")
    
    if args.integration:
        cmd.append("-m")
        cmd.append("integration")
    
    if args.performance:
        cmd.append("-m")
        cmd.append("performance")
    
    if args.coverage:
        cmd.extend(["--cov=crawlers", "--cov-report=html"])
    
    if args.markers:
        cmd.append("-m")
        cmd.append(args.markers)
    
    print(f"Running: {' '.join(cmd)}")
    print("="*60)
    
    result = subprocess.run(cmd)
    return result.returncode


def run_manual_tests():
    """Run manual tests directly"""
    print("\n" + "="*60)
    print("Running Manual Tests")
    print("="*60)
    
    from test_integration import run_comprehensive_test
    import asyncio
    
    asyncio.run(run_comprehensive_test())


def main():
    parser = argparse.ArgumentParser(description="Run crawler tests")
    parser.add_argument("--file", help="Specific test file to run (without .py)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--markers", "-m", help="Run tests with specific markers")
    parser.add_argument("--manual", action="store_true", help="Run manual comprehensive test")
    
    args = parser.parse_args()
    
    if args.manual:
        run_manual_tests()
    else:
        exit_code = run_pytest(args)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
