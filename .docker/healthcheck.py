#!/usr/bin/env python3
"""
Health check script for CorpusCallosum Docker container.

Verifies that the MCP server is running and responding correctly.
"""

import sys
import httpx
import json
import os
import time
from typing import Dict, Any


def check_mcp_server() -> bool:
    """Check if MCP server is responding correctly."""
    try:
        # Get configuration from environment
        host = os.getenv("CC_MCP_HOST", "localhost")
        port = int(os.getenv("CC_MCP_PORT", "8000"))
        
        # Try to connect to MCP server
        with httpx.Client(timeout=5.0) as client:
            # Check if server is running with a simple health endpoint
            response = client.get(f"http://{host}:{port}/health")
            
            if response.status_code == 200:
                return True
            else:
                print(f"MCP server returned status code: {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print("Cannot connect to MCP server")
        return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def check_database() -> bool:
    """Check if ChromaDB directory is accessible."""
    try:
        db_path = os.getenv("CC_DATABASE_PERSIST_DIRECTORY", "/home/corpus/data/chroma_store")
        
        # Check if database directory exists and is writable
        if not os.path.exists(db_path):
            os.makedirs(db_path, exist_ok=True)
        
        # Try to write a test file
        test_file = os.path.join(db_path, ".health_check")
        with open(test_file, "w") as f:
            f.write(str(time.time()))
        
        # Clean up test file
        os.remove(test_file)
        return True
        
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False


def main() -> None:
    """Run health checks and exit with appropriate status code."""
    print("Running CorpusCallosum health checks...")
    
    # Check database accessibility
    if not check_database():
        print("❌ Database health check failed")
        sys.exit(1)
    else:
        print("✅ Database health check passed")
    
    # Check MCP server (only if running as MCP server)
    if os.getenv("CC_SERVICE_TYPE", "mcp") == "mcp":
        if not check_mcp_server():
            print("❌ MCP server health check failed")
            sys.exit(1)
        else:
            print("✅ MCP server health check passed")
    
    print("✅ All health checks passed")
    sys.exit(0)


if __name__ == "__main__":
    main()