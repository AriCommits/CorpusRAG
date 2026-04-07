"""Secure environment variable and secrets management."""

import os
import warnings
from typing import Optional, Dict, Any, Union
from pathlib import Path
import json

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    warnings.warn(
        "keyring not available. Install with 'pip install keyring' for secure credential storage.",
        UserWarning
    )

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class SecretManager:
    """Secure management of secrets and environment variables."""
    
    def __init__(self, app_name: str = "corpus-callosum"):
        """Initialize secret manager.
        
        Args:
            app_name: Application name for keyring storage
        """
        self.app_name = app_name
        self.config_dir = Path.home() / f".{app_name.replace('-', '_')}"
        self.config_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Encrypted local storage fallback
        self.local_secrets_file = self.config_dir / "secrets.enc"
        self.key_file = self.config_dir / "key.enc"
        
        self._ensure_encryption_key()
    
    def _ensure_encryption_key(self) -> None:
        """Ensure encryption key exists for local storage."""
        if not CRYPTO_AVAILABLE:
            return
            
        if not self.key_file.exists():
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            self.key_file.chmod(0o600)
    
    def _get_cipher(self) -> Optional[Fernet]:
        """Get cipher for encryption/decryption."""
        if not CRYPTO_AVAILABLE or not self.key_file.exists():
            return None
        
        try:
            key = self.key_file.read_bytes()
            return Fernet(key)
        except Exception:
            return None
    
    def store_secret(self, key: str, value: str, use_keyring: bool = True) -> bool:
        """Store a secret securely.
        
        Args:
            key: Secret key/name
            value: Secret value
            use_keyring: Try to use system keyring first
            
        Returns:
            True if stored successfully
        """
        # Try system keyring first
        if use_keyring and KEYRING_AVAILABLE:
            try:
                keyring.set_password(self.app_name, key, value)
                return True
            except Exception:
                pass  # Fall back to local storage
        
        # Fall back to encrypted local storage
        return self._store_local_secret(key, value)
    
    def get_secret(self, key: str, default: Optional[str] = None, use_keyring: bool = True) -> Optional[str]:
        """Retrieve a secret.
        
        Args:
            key: Secret key/name
            default: Default value if not found
            use_keyring: Try to use system keyring first
            
        Returns:
            Secret value or default
        """
        # Try system keyring first
        if use_keyring and KEYRING_AVAILABLE:
            try:
                value = keyring.get_password(self.app_name, key)
                if value is not None:
                    return value
            except Exception:
                pass  # Fall back to local storage
        
        # Try encrypted local storage
        value = self._get_local_secret(key)
        if value is not None:
            return value
        
        # Try environment variable as last resort
        env_value = os.environ.get(key)
        if env_value is not None:
            # Warn about insecure storage
            warnings.warn(
                f"Secret '{key}' found in environment variable. "
                f"Consider using secure storage: secrets.store_secret('{key}', 'value')",
                UserWarning
            )
            return env_value
        
        return default
    
    def delete_secret(self, key: str, use_keyring: bool = True) -> bool:
        """Delete a secret.
        
        Args:
            key: Secret key/name
            use_keyring: Try to delete from system keyring too
            
        Returns:
            True if deleted successfully
        """
        deleted = False
        
        # Delete from keyring
        if use_keyring and KEYRING_AVAILABLE:
            try:
                keyring.delete_password(self.app_name, key)
                deleted = True
            except Exception:
                pass
        
        # Delete from local storage
        if self._delete_local_secret(key):
            deleted = True
        
        return deleted
    
    def _store_local_secret(self, key: str, value: str) -> bool:
        """Store secret in encrypted local file."""
        cipher = self._get_cipher()
        if not cipher:
            # No encryption available, warn and skip
            warnings.warn(
                f"Cannot store secret '{key}' securely. Install cryptography: pip install cryptography",
                UserWarning
            )
            return False
        
        try:
            # Load existing secrets
            secrets = {}
            if self.local_secrets_file.exists():
                encrypted_data = self.local_secrets_file.read_bytes()
                decrypted_data = cipher.decrypt(encrypted_data)
                secrets = json.loads(decrypted_data.decode())
            
            # Add new secret
            secrets[key] = value
            
            # Encrypt and save
            encrypted_data = cipher.encrypt(json.dumps(secrets).encode())
            self.local_secrets_file.write_bytes(encrypted_data)
            self.local_secrets_file.chmod(0o600)
            
            return True
        except Exception:
            return False
    
    def _get_local_secret(self, key: str) -> Optional[str]:
        """Get secret from encrypted local file."""
        cipher = self._get_cipher()
        if not cipher or not self.local_secrets_file.exists():
            return None
        
        try:
            encrypted_data = self.local_secrets_file.read_bytes()
            decrypted_data = cipher.decrypt(encrypted_data)
            secrets = json.loads(decrypted_data.decode())
            return secrets.get(key)
        except Exception:
            return None
    
    def _delete_local_secret(self, key: str) -> bool:
        """Delete secret from encrypted local file."""
        cipher = self._get_cipher()
        if not cipher or not self.local_secrets_file.exists():
            return False
        
        try:
            encrypted_data = self.local_secrets_file.read_bytes()
            decrypted_data = cipher.decrypt(encrypted_data)
            secrets = json.loads(decrypted_data.decode())
            
            if key in secrets:
                del secrets[key]
                
                # Re-encrypt and save
                encrypted_data = cipher.encrypt(json.dumps(secrets).encode())
                self.local_secrets_file.write_bytes(encrypted_data)
                return True
            
            return False
        except Exception:
            return False
    
    def list_secrets(self) -> list[str]:
        """List all stored secret keys (not values).
        
        Returns:
            List of secret key names
        """
        keys = set()
        
        # From local storage
        cipher = self._get_cipher()
        if cipher and self.local_secrets_file.exists():
            try:
                encrypted_data = self.local_secrets_file.read_bytes()
                decrypted_data = cipher.decrypt(encrypted_data)
                secrets = json.loads(decrypted_data.decode())
                keys.update(secrets.keys())
            except Exception:
                pass
        
        return list(keys)
    
    def migrate_from_env(self, env_vars: list[str], delete_from_env: bool = False) -> Dict[str, bool]:
        """Migrate secrets from environment variables to secure storage.
        
        Args:
            env_vars: List of environment variable names to migrate
            delete_from_env: Whether to delete from environment after migration
            
        Returns:
            Dict mapping env var names to success status
        """
        results = {}
        
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                success = self.store_secret(var, value)
                results[var] = success
                
                if success and delete_from_env:
                    del os.environ[var]
            else:
                results[var] = False
        
        return results


# Global secret manager instance
secrets = SecretManager()


def get_env_secure(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable or secret securely.
    
    This function first checks secure storage, then falls back to environment variables.
    
    Args:
        key: Environment variable or secret name
        default: Default value if not found
        
    Returns:
        Value from secure storage or environment, or default
    """
    return secrets.get_secret(key, default)


def set_env_secure(key: str, value: str) -> bool:
    """Set environment variable or secret securely.
    
    Args:
        key: Environment variable or secret name
        value: Value to store
        
    Returns:
        True if stored successfully
    """
    return secrets.store_secret(key, value)


def validate_required_secrets(required: list[str]) -> Dict[str, bool]:
    """Validate that required secrets are available.
    
    Args:
        required: List of required secret/env var names
        
    Returns:
        Dict mapping secret names to availability status
    """
    results = {}
    
    for secret_name in required:
        value = get_env_secure(secret_name)
        results[secret_name] = value is not None
    
    return results


def get_missing_secrets(required: list[str]) -> list[str]:
    """Get list of missing required secrets.
    
    Args:
        required: List of required secret names
        
    Returns:
        List of missing secret names
    """
    results = validate_required_secrets(required)
    return [name for name, available in results.items() if not available]