#!/usr/bin/env python3
"""CLI tool for managing Corpus Callosum MCP server API keys."""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ..utils.auth import MCPAuthenticator, AuthConfig


def get_auth_file() -> Path:
    """Get the path to the API keys file."""
    return Path.home() / ".corpus_callosum" / "api_keys.json"


def create_authenticator() -> MCPAuthenticator:
    """Create authenticator instance."""
    config = AuthConfig(enabled=True)
    return MCPAuthenticator(config, get_auth_file())


def generate_key(args) -> None:
    """Generate a new API key."""
    authenticator = create_authenticator()
    
    # Parse expiration
    expires_at = None
    if args.expires:
        try:
            if args.expires.endswith('d'):
                days = int(args.expires[:-1])
                expires_at = datetime.now() + timedelta(days=days)
            elif args.expires.endswith('h'):
                hours = int(args.expires[:-1])
                expires_at = datetime.now() + timedelta(hours=hours)
            else:
                # Assume it's a datetime string
                expires_at = datetime.fromisoformat(args.expires)
        except ValueError:
            print(f"❌ Invalid expiration format: {args.expires}")
            print("Use formats like '30d', '24h', or ISO datetime")
            sys.exit(1)
    
    # Parse permissions
    permissions = {"read": True, "write": True}
    if args.read_only:
        permissions["write"] = False
    if args.admin:
        permissions["admin"] = True
    
    # Generate key
    api_key = authenticator.api_key_manager.generate_api_key(
        name=args.name,
        permissions=permissions,
        expires_at=expires_at
    )
    
    print(f"🔑 Generated API key: {api_key}")
    print(f"📝 Name: {args.name}")
    print(f"🔐 Permissions: {permissions}")
    if expires_at:
        print(f"⏰ Expires: {expires_at.isoformat()}")
    print()
    print("⚠️  Store this key securely - it won't be displayed again!")


def list_keys(args) -> None:
    """List all API keys."""
    authenticator = create_authenticator()
    keys = authenticator.api_key_manager.list_api_keys()
    
    if not keys:
        print("No API keys found.")
        return
    
    print(f"Found {len(keys)} API key(s):")
    print()
    
    for key_preview, info in keys.items():
        print(f"🔑 {key_preview}")
        print(f"   Name: {info['name']}")
        print(f"   Created: {info['created_at']}")
        print(f"   Usage: {info['usage_count']} requests")
        if info['last_used']:
            print(f"   Last used: {info['last_used']}")
        if info['expires_at']:
            print(f"   Expires: {info['expires_at']}")
        print(f"   Permissions: {info['permissions']}")
        print()


def revoke_key(args) -> None:
    """Revoke an API key."""
    authenticator = create_authenticator()
    
    if authenticator.api_key_manager.revoke_api_key(args.key):
        print(f"✅ Revoked API key: {args.key}")
    else:
        print(f"❌ API key not found: {args.key}")
        sys.exit(1)


def test_key(args) -> None:
    """Test an API key."""
    authenticator = create_authenticator()
    
    key_info = authenticator.api_key_manager.validate_api_key(args.key)
    if key_info:
        print(f"✅ API key is valid")
        print(f"   Name: {key_info['name']}")
        print(f"   Permissions: {key_info['permissions']}")
        print(f"   Usage: {key_info['usage_count']} requests")
        if key_info['expires_at']:
            expires = datetime.fromisoformat(key_info['expires_at'])
            if expires > datetime.now():
                print(f"   Expires: {key_info['expires_at']}")
            else:
                print(f"   ❌ EXPIRED: {key_info['expires_at']}")
    else:
        print(f"❌ API key is invalid or expired: {args.key}")
        sys.exit(1)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Manage Corpus Callosum MCP Server API Keys",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate a new API key')
    gen_parser.add_argument('name', help='Human-readable name for the key')
    gen_parser.add_argument('--expires', help='Expiration (e.g., "30d", "24h", or ISO datetime)')
    gen_parser.add_argument('--read-only', action='store_true', help='Create read-only key')
    gen_parser.add_argument('--admin', action='store_true', help='Grant admin permissions')
    gen_parser.set_defaults(func=generate_key)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all API keys')
    list_parser.set_defaults(func=list_keys)
    
    # Revoke command
    revoke_parser = subparsers.add_parser('revoke', help='Revoke an API key')
    revoke_parser.add_argument('key', help='API key to revoke')
    revoke_parser.set_defaults(func=revoke_key)
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test if an API key is valid')
    test_parser.add_argument('key', help='API key to test')
    test_parser.set_defaults(func=test_key)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Ensure auth directory exists
    get_auth_file().parent.mkdir(parents=True, exist_ok=True)
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n❌ Cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()