"""Simple smoke-test to verify package imports work correctly.

Run directly: python tests/test_imports.py
"""

import sys
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    try:
        from config import BaseConfig

        print("✓ Configuration imports work")
        print("✓ Database imports work")

        config = BaseConfig()
        print(f"✓ BaseConfig created: LLM model = {config.llm.model}")

        print("\nAll imports successful!")
        return 0

    except Exception as e:
        print(f"✗ Import error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
