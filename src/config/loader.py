"""YAML configuration loader with deep merge support."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar

import yaml

from .base import BaseConfig

T = TypeVar("T", bound=BaseConfig)


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


def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML file.

    Args:
        path: Path to YAML file

    Returns:
        Dictionary with YAML contents

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return data or {}


def parse_env_overrides(prefix: str = "CC_") -> Dict[str, Any]:
    """Parse environment variables with given prefix into nested dict.

    Converts CC_LLM_MODEL=llama3 to {"llm": {"model": "llama3"}}

    Args:
        prefix: Environment variable prefix (default: CC_)

    Returns:
        Nested dictionary with environment overrides
    """
    result: Dict[str, Any] = {}

    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue

        # Remove prefix and split by underscore
        parts = key[len(prefix) :].lower().split("_")

        # Build nested dict
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
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
    """
    # Default base config path
    if base_path is None:
        base_path = Path("configs/base.yaml")

    # Load base config if it exists
    if base_path.exists():
        base_data = load_yaml(base_path)
    else:
        base_data = {}

    # Load tool-specific config
    tool_data = load_yaml(config_path)

    # Merge configs
    merged = deep_merge(base_data, tool_data)

    # Apply environment overrides
    env_overrides = parse_env_overrides()
    if env_overrides:
        merged = deep_merge(merged, env_overrides)

    # Create config instance
    return config_class.from_dict(merged)


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
