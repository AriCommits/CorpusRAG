#!/usr/bin/env python3
"""Comprehensive lint and format checker for CorpusCallosum.

This script ensures code passes all pre-commit checks before pushing to GitHub.
It runs Black, isort, Ruff, and optionally pytest.

Usage:
    python scripts/lint_and_format.py                  # Run all checks
    python scripts/lint_and_format.py --fix            # Auto-fix issues
    python scripts/lint_and_format.py --test           # Also run tests
    python scripts/lint_and_format.py --fix --test     # Fix + test
"""

import platform
import subprocess
import sys
from pathlib import Path

# ANSI color codes (disable on Windows)
_USE_COLORS = platform.system() != "Windows"
GREEN = "\033[0;32m" if _USE_COLORS else ""
YELLOW = "\033[1;33m" if _USE_COLORS else ""
RED = "\033[0;31m" if _USE_COLORS else ""
RESET = "\033[0m" if _USE_COLORS else ""

# Unicode symbols (fallback to ASCII on Windows)
CHECK = "✓" if _USE_COLORS else "+"
CROSS = "✗" if _USE_COLORS else "x"

PROJECT_ROOT = Path(__file__).parent.parent
PATHS = ["src", "tests", "scripts"]


def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 50)
    print(f"{YELLOW}{text}{RESET}")
    print("=" * 50)


def print_check(name: str, status: str, passed: bool) -> None:
    """Print check result."""
    symbol = CHECK if passed else CROSS
    color = GREEN if passed else RED
    print(f"{color}{symbol} {name}: {status}{RESET}")


def run_command(cmd: list) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"Command timed out: {' '.join(cmd)}"
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"
    except Exception as e:
        return False, str(e)


def check_black(fix: bool = False) -> bool:
    """Check code formatting with Black."""
    print(f"\n{YELLOW}Checking Black (code formatting)...{RESET}")
    cmd = ["python", "-m", "black"]
    if not fix:
        cmd.append("--check")
    cmd.extend(PATHS)

    passed, _ = run_command(cmd)
    if passed:
        print_check("Black", "passed", True)
    else:
        print_check("Black", "failed", False)
        if not fix:
            print(f"  Run: python -m black {' '.join(PATHS)}")

    return passed


def check_isort(fix: bool = False) -> bool:
    """Check import sorting with isort."""
    print(f"\n{YELLOW}Checking isort (import sorting)...{RESET}")
    cmd = ["python", "-m", "isort"]
    if not fix:
        cmd.append("--check-only")
    cmd.extend(PATHS)

    passed, _ = run_command(cmd)
    if passed:
        print_check("isort", "passed", True)
    else:
        print_check("isort", "failed", False)
        if not fix:
            print(f"  Run: python -m isort {' '.join(PATHS)}")

    return passed


def check_ruff(fix: bool = False) -> bool:
    """Check linting with Ruff."""
    print(f"\n{YELLOW}Checking Ruff (linting)...{RESET}")
    cmd = ["python", "-m", "ruff", "check"]
    if fix:
        cmd.append("--fix")
    cmd.extend(PATHS)

    passed, output = run_command(cmd)
    if passed:
        print_check("Ruff", "passed", True)
    else:
        print_check("Ruff", "failed", False)
        if output:
            if fix:
                print(
                    "\nRuff attempted auto-fixes. Remaining errors cannot be auto-fixed:"
                )
            else:
                print("\nRuff findings (first 30 lines):")
            # Print first 30 lines
            lines = output.split("\n")[:30]
            for line in lines:
                if line.strip():
                    print(f"  {line}")
            total_lines = len(output.split("\n"))
            if total_lines > 30:
                print(f"  ... and {total_lines - 30} more lines")

            if fix:
                print(f"\n{YELLOW}Manual fixes needed:{RESET}")
                print("  B904: Exception handling (raise ... from err)")
                print("  PLR0912: Too many branches (code complexity)")
                print("  PTH123/PTH100: Path.open() replacements")
                print("  B017: Blind exception assertions")
                print("  RUF043: Raw string patterns")
                print(f"\n{YELLOW}To see all errors:{RESET}")
                print("  python -m ruff check src tests scripts")

    return passed


def check_trailing_whitespace() -> bool:
    """Check for trailing whitespace."""
    print(f"\n{YELLOW}Checking for trailing whitespace...{RESET}")
    issues = []

    for path in PATHS:
        for py_file in Path(PROJECT_ROOT / path).rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if line.rstrip() != line and line.strip():  # Ignore empty lines
                        issues.append(f"{py_file.relative_to(PROJECT_ROOT)}:{i}")
            except Exception:
                pass

    if issues:
        print_check("Trailing whitespace", f"found {len(issues)} issues", False)
        for issue in issues[:10]:
            print(f"  {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
        return False
    else:
        print_check("Trailing whitespace", "passed", True)
        return True


def check_tests() -> bool:
    """Run pytest."""
    print(f"\n{YELLOW}Running pytest (unit tests)...{RESET}")
    cmd = ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-x"]

    passed, output = run_command(cmd)
    if passed:
        print_check("pytest", "passed", True)
    else:
        print_check("pytest", "failed", False)
        # Print last 50 lines of output
        lines = output.split("\n")[-50:]
        print("\nTest output (last 50 lines):")
        for line in lines:
            if line.strip():
                print(f"  {line}")

    return passed


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Lint and format checker for CorpusCallosum"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix formatting and linting issues",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Also run pytest after linting",
    )
    parser.add_argument(
        "--no-black",
        action="store_true",
        help="Skip Black formatting check",
    )
    parser.add_argument(
        "--no-isort",
        action="store_true",
        help="Skip isort import sorting check",
    )
    parser.add_argument(
        "--no-ruff",
        action="store_true",
        help="Skip Ruff linting check",
    )

    args = parser.parse_args()

    print_header("CorpusCallosum Lint & Format Check")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Paths to check: {', '.join(PATHS)}")
    if args.fix:
        print(f"{YELLOW}Mode: AUTO-FIX enabled{RESET}")
    if args.test:
        print(f"{YELLOW}Will run tests after checks{RESET}")

    results = []

    # Run checks
    if not args.no_black:
        results.append(check_black(fix=args.fix))

    if not args.no_isort:
        results.append(check_isort(fix=args.fix))

    if not args.no_ruff:
        results.append(check_ruff(fix=args.fix))

    results.append(check_trailing_whitespace())

    # Run tests if requested
    if args.test:
        results.append(check_tests())

    # Summary
    print_header("Summary")
    passed = sum(results)
    total = len(results)
    print(f"\nChecks passed: {passed}/{total}")

    if all(results):
        print_header(f"{CHECK} All checks passed!")
        print(f"{GREEN}Ready to push to GitHub{RESET}\n")
        return 0
    else:
        print_header(f"{CROSS} Some checks failed")
        if not args.fix:
            print(f"\n{YELLOW}To fix issues automatically, run:{RESET}")
            print("  python scripts/lint_and_format.py --fix\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
