#!/usr/bin/env python3
"""
Manual sync command for Homeschool project.
Run with: python -m homeschool sync
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Main entry point for the sync command."""
    print("Starting manual sync process...")
    
    # Change to the .docker directory where docker-compose is located
    docker_dir = Path(__file__).parent.parent / ".docker"
    
    if not docker_dir.exists():
        print(f"Error: Docker directory not found at {docker_dir}")
        sys.exit(1)
    
    # Run docker compose to start the sync worker
    try:
        print(f"Running docker compose from {docker_dir}")
        result = subprocess.run(
            ["docker", "compose", "run", "--rm", "sync_worker"],
            cwd=docker_dir,
            check=True
        )
        print("Sync completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Sync failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("Error: Docker command not found. Please install Docker.")
        sys.exit(1)

if __name__ == "__main__":
    main()