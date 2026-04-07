#!/usr/bin/env python3
"""CLI tool for managing Corpus Callosum secrets and environment variables."""

import argparse
import getpass
import sys
from typing import List

from ..utils.secrets import secrets, get_env_secure, validate_required_secrets


def store_secret(args) -> None:
    """Store a secret securely."""
    if args.value:
        value = args.value
    else:
        # Prompt for value securely
        value = getpass.getpass(f"Enter value for '{args.key}': ")
    
    if not value:
        print("❌ Value cannot be empty")
        sys.exit(1)
    
    success = secrets.store_secret(args.key, value, use_keyring=not args.no_keyring)
    
    if success:
        print(f"✅ Stored secret '{args.key}' securely")
    else:
        print(f"❌ Failed to store secret '{args.key}'")
        print("Make sure you have keyring or cryptography installed:")
        print("  pip install keyring cryptography")
        sys.exit(1)


def get_secret(args) -> None:
    """Retrieve a secret."""
    value = get_env_secure(args.key)
    
    if value:
        if args.show:
            print(f"🔑 {args.key}: {value}")
        else:
            print(f"✅ Secret '{args.key}' is set")
    else:
        print(f"❌ Secret '{args.key}' not found")
        sys.exit(1)


def delete_secret(args) -> None:
    """Delete a secret."""
    success = secrets.delete_secret(args.key, use_keyring=not args.no_keyring)
    
    if success:
        print(f"✅ Deleted secret '{args.key}'")
    else:
        print(f"❌ Secret '{args.key}' not found or could not be deleted")


def list_secrets(args) -> None:
    """List all stored secrets."""
    secret_keys = secrets.list_secrets()
    
    if not secret_keys:
        print("No secrets stored.")
        return
    
    print(f"Found {len(secret_keys)} secret(s):")
    for key in sorted(secret_keys):
        # Check if it has a value
        value = get_env_secure(key)
        status = "✅" if value else "❌"
        print(f"  {status} {key}")


def migrate_secrets(args) -> None:
    """Migrate environment variables to secure storage."""
    env_vars = args.variables
    
    if not env_vars:
        # Common environment variables to migrate
        common_vars = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "OLLAMA_API_KEY", 
            "HF_TOKEN",
            "HUGGINGFACE_TOKEN",
            "GOOGLE_API_KEY",
            "AZURE_OPENAI_KEY",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY"
        ]
        
        print("No variables specified. Checking common ones:")
        env_vars = []
        import os
        for var in common_vars:
            if var in os.environ:
                env_vars.append(var)
                print(f"  Found: {var}")
        
        if not env_vars:
            print("No common environment variables found.")
            return
        
        if not args.yes:
            response = input(f"\nMigrate {len(env_vars)} variable(s)? [y/N]: ")
            if response.lower() not in ["y", "yes"]:
                print("Cancelled.")
                return
    
    results = secrets.migrate_from_env(env_vars, delete_from_env=args.delete)
    
    print(f"\nMigration results:")
    for var, success in results.items():
        status = "✅" if success else "❌"
        action = "migrated" if success else "failed"
        print(f"  {status} {var}: {action}")
    
    successful = sum(results.values())
    print(f"\n{successful}/{len(results)} variables migrated successfully.")


def validate_secrets(args) -> None:
    """Validate that required secrets are available."""
    required = args.secrets
    
    if not required:
        # Default required secrets for Corpus Callosum
        required = [
            "OPENAI_API_KEY",  # For LLM operations
            "OLLAMA_HOST",     # For local LLM
        ]
    
    results = validate_required_secrets(required)
    
    print("Secret validation results:")
    missing = []
    
    for secret, available in results.items():
        status = "✅" if available else "❌"
        state = "available" if available else "missing"
        print(f"  {status} {secret}: {state}")
        
        if not available:
            missing.append(secret)
    
    if missing:
        print(f"\n❌ {len(missing)} secret(s) missing:")
        for secret in missing:
            print(f"   Set with: secrets store {secret}")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(required)} required secrets are available.")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Manage Corpus Callosum secrets and environment variables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  secrets store OPENAI_API_KEY                 # Prompt for API key
  secrets store OPENAI_API_KEY sk-abc123      # Store directly
  secrets get OPENAI_API_KEY                  # Check if set
  secrets get OPENAI_API_KEY --show           # Show actual value
  secrets list                                # List all secrets
  secrets migrate OPENAI_API_KEY HF_TOKEN     # Migrate from env vars
  secrets migrate --delete                    # Auto-migrate common vars
  secrets validate                            # Check required secrets
  secrets delete OPENAI_API_KEY               # Delete a secret
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Store command
    store_parser = subparsers.add_parser('store', help='Store a secret securely')
    store_parser.add_argument('key', help='Secret name/key')
    store_parser.add_argument('value', nargs='?', help='Secret value (will prompt if not provided)')
    store_parser.add_argument('--no-keyring', action='store_true', help='Skip system keyring')
    store_parser.set_defaults(func=store_secret)
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Retrieve a secret')
    get_parser.add_argument('key', help='Secret name/key')
    get_parser.add_argument('--show', action='store_true', help='Show the actual value')
    get_parser.set_defaults(func=get_secret)
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a secret')
    delete_parser.add_argument('key', help='Secret name/key')
    delete_parser.add_argument('--no-keyring', action='store_true', help='Skip system keyring')
    delete_parser.set_defaults(func=delete_secret)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all stored secrets')
    list_parser.set_defaults(func=list_secrets)
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate environment variables to secure storage')
    migrate_parser.add_argument('variables', nargs='*', help='Environment variable names to migrate')
    migrate_parser.add_argument('--delete', action='store_true', help='Delete from environment after migration')
    migrate_parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    migrate_parser.set_defaults(func=migrate_secrets)
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate required secrets')
    validate_parser.add_argument('secrets', nargs='*', help='Secret names to validate')
    validate_parser.set_defaults(func=validate_secrets)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
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