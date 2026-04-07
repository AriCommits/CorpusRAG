"""YAML configuration loader with deep merge support."""

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Set, Type, TypeVar

import yaml

from .base import BaseConfig
from ..utils.security import PathTraversalError, SecurityError, validate_file_path

T = TypeVar("T", bound=BaseConfig)

# Configure logger
logger = logging.getLogger(__name__)

# Allowed top-level configuration keys
ALLOWED_CONFIG_KEYS: Set[str] = {
    "llm",
    "embedding",
    "database",
    "paths",
    "auth",
    "rag",
    "tools",
    "logging",
    "monitoring",
}

# Dangerous patterns to scan for in YAML content
DANGEROUS_PATTERNS = [
    r"!!python/",
    r"!!obj/",
    r"!!ruby/",
    r"!!perl/",
    r"eval\(",
    r"exec\(",
    r"subprocess",
    r"__import__",
    r"os\.system",
    r"os\.popen",
    r"commands\.",
    r"pickle\.",
    r"marshal\.",
]

# Maximum file sizes and depths
MAX_CONFIG_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_NESTING_DEPTH = 5
MAX_ENV_VALUE_LENGTH = 10 * 1024  # 10KB


def _calculate_checksum(file_path: Path) -> str:
    """Calculate SHA-256 checksum of file.

    Args:
        file_path: Path to file

    Returns:
        Hex digest of SHA-256 hash
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def _scan_for_dangerous_patterns(content: str) -> None:
    """Scan YAML content for dangerous patterns.

    Args:
        content: YAML content as string

    Raises:
        SecurityError: If dangerous patterns are detected
    """
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            raise SecurityError(
                f"Suspicious pattern detected in configuration: {pattern}"
            )


def _check_nesting_depth(obj: Any, max_depth: int = MAX_NESTING_DEPTH, current_depth: int = 0) -> None:
    """Validate nesting depth doesn't exceed maximum.

    Args:
        obj: Object to check
        max_depth: Maximum allowed depth
        current_depth: Current recursion depth

    Raises:
        SecurityError: If nesting depth exceeded
    """
    if current_depth > max_depth:
        raise SecurityError(
            f"Configuration nesting depth ({current_depth}) exceeds maximum ({max_depth})"
        )

    if isinstance(obj, dict):
        for value in obj.values():
            _check_nesting_depth(value, max_depth, current_depth + 1)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _check_nesting_depth(item, max_depth, current_depth + 1)


def _validate_config_keys(data: Dict[str, Any]) -> None:
    """Validate that all top-level keys are allowed.

    Args:
        data: Configuration dictionary

    Raises:
        SecurityError: If unknown keys found
    """
    unknown_keys = set(data.keys()) - ALLOWED_CONFIG_KEYS
    if unknown_keys:
        raise SecurityError(
            f"Unknown configuration keys: {unknown_keys}. "
            f"Allowed keys: {ALLOWED_CONFIG_KEYS}"
        )


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries (override takes precedence).

    Args:
        base: Base dictionary
        override: Dictionary with override values

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def load_yaml(path: Path, validate_schema: bool = True) -> Dict[str, Any]:
    """Load YAML file with security validation.

    Args:
        path: Path to YAML file
        validate_schema: Whether to validate configuration schema

    Returns:
        Dictionary with YAML contents

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is invalid
        SecurityError: If security checks fail
        PathTraversalError: If path traversal detected
    """
    # Validate file path
    validated_path = validate_file_path(path, must_exist=True)

    # Check file size
    file_size = validated_path.stat().st_size
    if file_size > MAX_CONFIG_FILE_SIZE:
        raise SecurityError(
            f"Configuration file too large: {file_size} bytes (max: {MAX_CONFIG_FILE_SIZE})"
        )

    logger.info(f"Loading configuration from {validated_path}")

    # Read file content
    try:
        with open(validated_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, OSError) as e:
        raise SecurityError(f"Failed to read configuration file: {e}")

    # Scan for dangerous patterns
    _scan_for_dangerous_patterns(content)

    # Parse YAML safely
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise SecurityError(f"Invalid YAML configuration: {e}")

    # Ensure it's a dictionary
    if not isinstance(data, dict):
        raise SecurityError("Configuration must be a dictionary at top level")

    # Validate keys if requested
    if validate_schema:
        _validate_config_keys(data)

    # Check nesting depth
    _check_nesting_depth(data)

    logger.info(f"Successfully loaded configuration from {validated_path}")

    return data or {}


def parse_env_overrides(prefix: str = "CC_") -> Dict[str, Any]:
    """Parse environment variables with given prefix into nested dict.

    Converts CC_LLM_MODEL=llama3 to {"llm": {"model": "llama3"}}

    Args:
        prefix: Environment variable prefix (default: CC_)

    Returns:
        Nested dictionary with environment overrides

    Raises:
        SecurityError: If validation fails
    """
    result: Dict[str, Any] = {}

    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue

        # Remove prefix and split by underscore
        parts = key[len(prefix):].lower().split("_")

        # Validate key parts are alphanumeric
        for part in parts:
            if not part.isalnum():
                raise SecurityError(
                    f"Invalid environment variable format: {key}. "
                    f"Key parts must be alphanumeric."
                )

        # Validate value length
        if len(value) > MAX_ENV_VALUE_LENGTH:
            raise SecurityError(
                f"Environment variable value too long for {key}: "
                f"{len(value)} bytes (max: {MAX_ENV_VALUE_LENGTH})"
            )

        # Build nested dict
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                raise SecurityError(
                    f"Configuration conflict: {part} cannot be both "
                    f"a value and a container"
                )
            current = current[part]

        # Set final value (try to parse as int/float/bool)
        final_key = parts[-1]
        parsed_value: Any = value

        if value.lower() in ("true", "false"):
            parsed_value = value.lower() == "true"
        elif value.isdigit():
            parsed_value = int(value)
        elif value.replace(".", "", 1).isdigit():
            try:
                parsed_value = float(value)
            except ValueError:
                pass

        current[final_key] = parsed_value

    logger.debug(f"Parsed {len(result)} environment variable overrides")

    return result


def load_config(
    config_path: Path,
    base_path: Optional[Path] = None,
    config_class: Type[T] = BaseConfig,  # type: ignore
) -> T:
    """Load configuration with hierarchical merging.

    Loading order (later takes precedence):
    1. Base config (if provided)
    2. Tool-specific config
    3. Environment variables (CC_* prefix)

    Args:
        config_path: Path to tool-specific config file
        base_path: Path to base config file (default: configs/base.yaml)
        config_class: Config class to instantiate (default: BaseConfig)

    Returns:
        Config instance

    Raises:
        FileNotFoundError: If config files don't exist
        yaml.YAMLError: If YAML is invalid
        SecurityError: If security checks fail
    """
    # Default base config path
    if base_path is None:
        base_path = Path("configs/base.yaml")

    # Load base config if it exists
    if base_path.exists():
        base_data = load_yaml(base_path, validate_schema=True)
    else:
        base_data = {}

    # Load tool-specific config
    tool_data = load_yaml(config_path, validate_schema=True)

    # Merge configs
    merged = deep_merge(base_data, tool_data)

    # Apply environment overrides
    try:
        env_overrides = parse_env_overrides()
        if env_overrides:
            merged = deep_merge(merged, env_overrides)
    except SecurityError as e:
        logger.error(f"Failed to parse environment overrides: {e}")
        raise

    # Log configuration summary (without sensitive values)
    logger.info(f"Configuration loaded with {len(merged)} top-level sections")

    # Create config instance
    return config_class.from_dict(merged)  # type: ignore


def merge_configs(base: BaseConfig, override: BaseConfig) -> BaseConfig:
    """Merge two BaseConfig instances (override takes precedence).

    Args:
        base: Base configuration
        override: Override configuration

    Returns:
        Merged configuration
    """
    base_dict = base.to_dict()
    override_dict = override.to_dict()
    merged_dict = deep_merge(base_dict, override_dict)
    return BaseConfig.from_dict(merged_dict)
