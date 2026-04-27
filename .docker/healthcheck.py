#!/usr/bin/env python3
"""Health check script for CorpusRAG Docker container."""

import os
import sys

import httpx


def check_mcp_server() -> bool:
    """Check if MCP server health endpoint responds."""
    host = os.getenv("CORPUSRAG_MCP_HOST", "localhost")
    port = int(os.getenv("CORPUSRAG_MCP_PORT", "8000"))
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"http://{host}:{port}/health")
            return resp.status_code == 200
    except Exception as e:
        print(f"MCP server check failed: {e}")
        return False


def check_database() -> bool:
    """Check if database directory is accessible."""
    db_path = os.getenv(
        "CORPUSRAG_DATABASE_PERSIST_DIRECTORY", "/home/corpus/data/chroma_store"
    )
    try:
        os.makedirs(db_path, exist_ok=True)
        test_file = os.path.join(db_path, ".health_check")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return True
    except Exception as e:
        print(f"Database check failed: {e}")
        return False


def main() -> None:
    """Run health checks."""
    if not check_database():
        sys.exit(1)
    if not check_mcp_server():
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
