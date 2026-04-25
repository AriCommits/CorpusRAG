"""Unit tests for configuration system."""

import os
from pathlib import Path

import pytest
import yaml

from config import (
    BaseConfig,
    DatabaseConfig,
    EmbeddingConfig,
    LLMConfig,
    PathsConfig,
    load_config,
    merge_configs,
)
from config.loader import deep_merge, parse_env_overrides


class TestLLMConfig:
    """Tests for LLMConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default LLM config values."""
        config = LLMConfig()
        assert config.endpoint == "http://localhost:11434"
        assert config.model == "gemma4:26b-a4b-it-q4_K_M"
        assert config.timeout_seconds == 120.0
        assert config.temperature == 0.7
        assert config.max_tokens is None

    def test_custom_values(self) -> None:
        """Test custom LLM config values."""
        config = LLMConfig(
            endpoint="http://example.com:11434",
            model="mistral",
            timeout_seconds=60.0,
            temperature=0.5,
            max_tokens=1024,
        )
        assert config.endpoint == "http://example.com:11434"
        assert config.model == "mistral"
        assert config.timeout_seconds == 60.0
        assert config.temperature == 0.5
        assert config.max_tokens == 1024


class TestEmbeddingConfig:
    """Tests for EmbeddingConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default embedding config values."""
        config = EmbeddingConfig()
        assert config.backend == "ollama"
        assert config.model == "embeddinggemma"
        assert config.dimensions is None

    def test_custom_values(self) -> None:
        """Test custom embedding config values."""
        config = EmbeddingConfig(
            backend="sentence-transformers",
            model="all-MiniLM-L6-v2",
            dimensions=384,
        )
        assert config.backend == "sentence-transformers"
        assert config.model == "all-MiniLM-L6-v2"
        assert config.dimensions == 384


class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default database config values."""
        config = DatabaseConfig()
        assert config.backend == "chromadb"
        assert config.mode == "persistent"
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.persist_directory == Path("./chroma_store")

    def test_custom_values(self) -> None:
        """Test custom database config values."""
        config = DatabaseConfig(
            backend="chromadb",
            mode="http",
            host="192.168.1.100",
            port=9000,
            persist_directory=Path("/data/chroma"),
        )
        assert config.backend == "chromadb"
        assert config.mode == "http"
        assert config.host == "192.168.1.100"
        assert config.port == 9000
        assert config.persist_directory == Path("/data/chroma")


class TestPathsConfig:
    """Tests for PathsConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default paths config values."""
        config = PathsConfig()
        assert config.vault == Path("./vault")
        assert config.scratch_dir == Path("./scratch")
        assert config.output_dir == Path("./output")

    def test_custom_values(self) -> None:
        """Test custom paths config values."""
        config = PathsConfig(
            vault=Path("~/Documents/vault"),
            scratch_dir=Path("/tmp/scratch"),
            output_dir=Path("~/output"),
        )
        assert config.vault == Path("~/Documents/vault")
        assert config.scratch_dir == Path("/tmp/scratch")
        assert config.output_dir == Path("~/output")


class TestBaseConfig:
    """Tests for BaseConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default base config values."""
        config = BaseConfig()
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.embedding, EmbeddingConfig)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.paths, PathsConfig)

    def test_from_dict_minimal(self) -> None:
        """Test creating config from minimal dict."""
        data = {"llm": {"model": "mistral"}}
        config = BaseConfig.from_dict(data)
        assert config.llm.model == "mistral"
        assert config.llm.endpoint == "http://localhost:11434"  # from override

    def test_from_dict_complete(self) -> None:
        """Test creating config from complete dict."""
        data = {
            "llm": {
                "endpoint": "http://example.com:11434",
                "model": "mistral",
                "timeout_seconds": 60.0,
                "temperature": 0.5,
            },
            "embedding": {"backend": "sentence-transformers", "model": "test-model"},
            "database": {"mode": "http", "port": 9000},
            "paths": {"vault": "/data/vault"},
        }
        config = BaseConfig.from_dict(data)
        assert config.llm.endpoint == "http://example.com:11434"
        assert config.embedding.backend == "sentence-transformers"
        assert config.database.mode == "http"
        assert config.paths.vault == Path("/data/vault")

    def test_from_dict_path_conversion(self) -> None:
        """Test path string to Path conversion."""
        data = {
            "database": {"persist_directory": "/data/chroma"},
            "paths": {
                "vault": "~/vault",
                "scratch_dir": "/tmp/scratch",
                "output_dir": "./output",
            },
        }
        config = BaseConfig.from_dict(data)
        assert config.database.persist_directory == Path("/data/chroma")
        assert config.paths.vault == Path("~/vault")
        assert config.paths.scratch_dir == Path("/tmp/scratch")
        assert config.paths.output_dir == Path("./output")

    def test_to_dict(self) -> None:
        """Test converting config to dict."""
        config = BaseConfig()
        data = config.to_dict()
        assert "llm" in data
        assert "embedding" in data
        assert "database" in data
        assert "paths" in data
        assert data["llm"]["model"] == "gemma4:26b-a4b-it-q4_K_M"
        assert isinstance(data["paths"]["vault"], str)


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_merge_flat_dicts(self) -> None:
        """Test merging flat dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_dicts(self) -> None:
        """Test merging nested dictionaries."""
        base = {"llm": {"model": "gemma4:26b-a4b-it-q4_K_M", "temperature": 0.7}}
        override = {"llm": {"temperature": 0.5}}
        result = deep_merge(base, override)
        assert result == {"llm": {"model": "gemma4:26b-a4b-it-q4_K_M", "temperature": 0.5}}

    def test_merge_deep_nested(self) -> None:
        """Test merging deeply nested dictionaries."""
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"c": 99}}}
        result = deep_merge(base, override)
        assert result == {"a": {"b": {"c": 99, "d": 2}}}

    def test_merge_non_dict_override(self) -> None:
        """Test overriding dict with non-dict value."""
        base = {"a": {"b": 1}}
        override = {"a": "string"}
        result = deep_merge(base, override)
        assert result == {"a": "string"}


class TestParseEnvOverrides:
    """Tests for parse_env_overrides function."""

    def test_empty_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test with no CC_ variables."""
        # Clear all CC_ vars
        for key in list(os.environ.keys()):
            if key.startswith("CC_"):
                monkeypatch.delenv(key, raising=False)
        result = parse_env_overrides()
        assert result == {}

    def test_single_level_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test single-level variable."""
        monkeypatch.setenv("CC_MODEL", "mistral")
        result = parse_env_overrides()
        assert result == {"model": "mistral"}

    def test_nested_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test nested variable."""
        monkeypatch.setenv("CC_LLM_MODEL", "mistral")
        result = parse_env_overrides()
        assert result == {"llm": {"model": "mistral"}}

    def test_deep_nested_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test deeply nested variable."""
        monkeypatch.setenv("CC_DATABASE_CONFIG_PORT", "9000")
        result = parse_env_overrides()
        assert result == {"database": {"config": {"port": 9000}}}

    def test_type_parsing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test automatic type parsing."""
        # CC_X_Y parses to nested {"x": {"y": value}}, so use flat names
        monkeypatch.setenv("CC_INT", "42")
        monkeypatch.setenv("CC_FLOAT", "3.14")
        monkeypatch.setenv("CC_BOOLTRUE", "true")
        monkeypatch.setenv("CC_BOOLFALSE", "false")
        monkeypatch.setenv("CC_STRING", "hello")
        result = parse_env_overrides()
        assert result["int"] == 42
        assert result["float"] == 3.14
        assert result["booltrue"] is True
        assert result["boolfalse"] is False
        assert result["string"] == "hello"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_simple_config(self, tmp_path: Path) -> None:
        """Test loading a simple config file."""
        config_file = tmp_path / "config.yaml"
        config_data = {"llm": {"model": "mistral"}, "embedding": {"backend": "ollama"}}
        with config_file.open("w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)
        assert config.llm.model == "mistral"
        assert config.embedding.backend == "ollama"

    def test_load_with_base_config(self, tmp_path: Path) -> None:
        """Test loading with base config merging."""
        base_file = tmp_path / "base.yaml"
        tool_file = tmp_path / "tool.yaml"

        base_data = {"llm": {"model": "gemma4:26b-a4b-it-q4_K_M", "temperature": 0.7}}
        tool_data = {"llm": {"temperature": 0.5}}

        with base_file.open("w") as f:
            yaml.dump(base_data, f)
        with tool_file.open("w") as f:
            yaml.dump(tool_data, f)

        config = load_config(tool_file, base_path=base_file)
        assert config.llm.model == "gemma4:26b-a4b-it-q4_K_M"  # from base
        assert config.llm.temperature == 0.5  # overridden

    def test_load_with_env_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading with environment variable override."""
        config_file = tmp_path / "config.yaml"
        config_data = {"llm": {"model": "gemma4:26b-a4b-it-q4_K_M"}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.setenv("CC_LLM_MODEL", "mistral")
        config = load_config(config_file)
        assert config.llm.model == "mistral"

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")


class TestMergeConfigs:
    """Tests for merge_configs function."""

    def test_merge_two_configs(self) -> None:
        """Test merging two BaseConfig instances."""
        base = BaseConfig()
        base_endpoint = base.llm.endpoint
        override = BaseConfig()
        override.llm.model = "mistral"
        override.llm.temperature = 0.5

        result = merge_configs(base, override)
        assert result.llm.model == "mistral"
        assert result.llm.temperature == 0.5
        assert result.llm.endpoint == base_endpoint
