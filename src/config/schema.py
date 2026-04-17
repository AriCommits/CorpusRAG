"""Validation schemas for configuration."""

from pathlib import Path
from typing import Any


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


def validate_llm_config(config: dict[str, Any]) -> list[str]:
    """Validate LLM configuration.

    Args:
        config: LLM config dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if "endpoint" in config and not isinstance(config["endpoint"], str):
        errors.append("llm.endpoint must be a string")

    if "model" in config and not isinstance(config["model"], str):
        errors.append("llm.model must be a string")

    if "timeout_seconds" in config:
        if not isinstance(config["timeout_seconds"], (int, float)):
            errors.append("llm.timeout_seconds must be a number")
        elif config["timeout_seconds"] <= 0:
            errors.append("llm.timeout_seconds must be positive")

    if "temperature" in config:
        if not isinstance(config["temperature"], (int, float)):
            errors.append("llm.temperature must be a number")
        elif not 0 <= config["temperature"] <= 2:
            errors.append("llm.temperature must be between 0 and 2")

    if "max_tokens" in config and config["max_tokens"] is not None:
        if not isinstance(config["max_tokens"], int):
            errors.append("llm.max_tokens must be an integer")
        elif config["max_tokens"] <= 0:
            errors.append("llm.max_tokens must be positive")

    return errors


def validate_embedding_config(config: dict[str, Any]) -> list[str]:
    """Validate embedding configuration.

    Args:
        config: Embedding config dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if "backend" in config:
        if not isinstance(config["backend"], str):
            errors.append("embedding.backend must be a string")
        elif config["backend"] not in ("ollama", "sentence-transformers"):
            errors.append(
                "embedding.backend must be 'ollama' or 'sentence-transformers'"
            )

    if "model" in config and not isinstance(config["model"], str):
        errors.append("embedding.model must be a string")

    if "dimensions" in config and config["dimensions"] is not None:
        if not isinstance(config["dimensions"], int):
            errors.append("embedding.dimensions must be an integer")
        elif config["dimensions"] <= 0:
            errors.append("embedding.dimensions must be positive")

    return errors


def validate_database_config(config: dict[str, Any]) -> list[str]:
    """Validate database configuration.

    Args:
        config: Database config dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if "backend" in config:
        if not isinstance(config["backend"], str):
            errors.append("database.backend must be a string")
        elif config["backend"] != "chromadb":
            errors.append("database.backend must be 'chromadb'")

    if "mode" in config:
        if not isinstance(config["mode"], str):
            errors.append("database.mode must be a string")
        elif config["mode"] not in ("persistent", "http"):
            errors.append("database.mode must be 'persistent' or 'http'")

    if "host" in config and not isinstance(config["host"], str):
        errors.append("database.host must be a string")

    if "port" in config:
        if not isinstance(config["port"], int):
            errors.append("database.port must be an integer")
        elif not 1 <= config["port"] <= 65535:
            errors.append("database.port must be between 1 and 65535")

    return errors


def validate_paths_config(config: dict[str, Any]) -> list[str]:
    """Validate paths configuration.

    Args:
        config: Paths config dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    for key in ["vault", "scratch_dir", "output_dir"]:
        if key in config:
            value = config[key]
            if not isinstance(value, (str, Path)):
                errors.append(f"paths.{key} must be a string or Path")

    return errors


def validate_video_config(config: dict[str, Any]) -> list[str]:
    """Validate video configuration.

    Args:
        config: Video config dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Validate transcription settings
    if "whisper_model" in config and not isinstance(config["whisper_model"], str):
        errors.append("video.whisper_model must be a string")

    if "whisper_device" in config:
        if not isinstance(config["whisper_device"], str):
            errors.append("video.whisper_device must be a string")
        elif config["whisper_device"] not in ("cuda", "cpu"):
            errors.append("video.whisper_device must be 'cuda' or 'cpu'")

    if "whisper_compute_type" in config:
        if not isinstance(config["whisper_compute_type"], str):
            errors.append("video.whisper_compute_type must be a string")
        elif config["whisper_compute_type"] not in ("float16", "float32", "int8"):
            errors.append(
                "video.whisper_compute_type must be 'float16', 'float32', or 'int8'"
            )

    if "whisper_language" in config and config["whisper_language"] is not None:
        if not isinstance(config["whisper_language"], str):
            errors.append("video.whisper_language must be a string or null")

    if "models_dir" in config:
        if not isinstance(config["models_dir"], (str, Path)):
            errors.append("video.models_dir must be a string or Path")

    # Validate cleaning settings
    if "clean_model" in config and not isinstance(config["clean_model"], str):
        errors.append("video.clean_model must be a string")

    if "clean_ollama_host" in config and not isinstance(
        config["clean_ollama_host"], str
    ):
        errors.append("video.clean_ollama_host must be a string")

    if "clean_prompt" in config and not isinstance(config["clean_prompt"], str):
        errors.append("video.clean_prompt must be a string")

    # Validate output settings
    if "output_format" in config:
        if not isinstance(config["output_format"], str):
            errors.append("video.output_format must be a string")
        elif config["output_format"] not in ("markdown", "text", "json"):
            errors.append("video.output_format must be 'markdown', 'text', or 'json'")

    if "include_timestamps" in config and not isinstance(
        config["include_timestamps"], bool
    ):
        errors.append("video.include_timestamps must be a boolean")

    if "collection_prefix" in config and not isinstance(
        config["collection_prefix"], str
    ):
        errors.append("video.collection_prefix must be a string")

    if "supported_extensions" in config:
        if not isinstance(config["supported_extensions"], list):
            errors.append("video.supported_extensions must be a list")
        else:
            for ext in config["supported_extensions"]:
                if not isinstance(ext, str):
                    errors.append(
                        "video.supported_extensions must be a list of strings"
                    )
                elif not ext.startswith("."):
                    errors.append("video.supported_extensions must start with '.'")

    return errors


def validate_config(config_dict: dict[str, Any]) -> None:
    """Validate complete configuration dictionary.

    Args:
        config_dict: Configuration dictionary to validate

    Raises:
        ConfigValidationError: If validation fails
    """
    all_errors = []

    if "llm" in config_dict:
        all_errors.extend(validate_llm_config(config_dict["llm"]))

    if "embedding" in config_dict:
        all_errors.extend(validate_embedding_config(config_dict["embedding"]))

    if "database" in config_dict:
        all_errors.extend(validate_database_config(config_dict["database"]))

    if "paths" in config_dict:
        all_errors.extend(validate_paths_config(config_dict["paths"]))

    if "video" in config_dict:
        all_errors.extend(validate_video_config(config_dict["video"]))

    if all_errors:
        raise ConfigValidationError(
            "Configuration validation failed:\n"
            + "\n".join(f"  - {error}" for error in all_errors)
        )
