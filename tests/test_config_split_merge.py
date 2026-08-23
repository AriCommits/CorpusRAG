"""Tests for the scoped config split and the split-then-merge equivalence.

Covers the restructuring of the monolithic example config into a core
``configs/base.yaml`` plus scoped tool files, and verifies that loading a
scoped tool file layered on the base resolves to the same configuration as
loading the equivalent combined document in one shot.
"""

import os
from pathlib import Path

import pytest
import yaml
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from config.base import BaseConfig
from config.loader import load_config

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"


@pytest.fixture(autouse=True)
def _clear_cc_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove CC_* env overrides so they cannot perturb the equivalence."""
    for key in list(os.environ):
        if key.startswith("CC_"):
            monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# Strategies for the combined configuration document
# ---------------------------------------------------------------------------

# Safe text: letters/digits/space only, so YAML round-trips cleanly and never
# collides with the loader's dangerous-pattern scan. ``subprocess`` is the
# only letter-only pattern in that scan (the rest need punctuation).
_safe_text = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ",
    max_size=12,
).filter(lambda s: "subprocess" not in s.lower())
_scalars = st.one_of(
    st.integers(min_value=-1000, max_value=1000),
    st.booleans(),
    _safe_text,
    st.none(),
)
_yaml_keys = st.sampled_from(["a", "b", "c", "x", "y", "opt", "flag"])


def _tool_section() -> st.SearchStrategy:
    """A shallow mapping of scalars, optionally one level of nested mapping."""
    inner = st.dictionaries(_yaml_keys, _scalars, max_size=4)
    return st.dictionaries(_yaml_keys, st.one_of(_scalars, inner), max_size=5)


@st.composite
def _combined_config(draw) -> dict:
    """Build a combined config with the 4 typed sections + rag/video tools."""
    llm = {
        "backend": "ollama",
        "model": draw(st.sampled_from(["gemma4:26b", "mistral:latest", "llama3"])),
        "temperature": draw(st.floats(0.0, 2.0, allow_nan=False, allow_infinity=False)),
        "timeout_seconds": draw(st.floats(1.0, 600.0, allow_nan=False, allow_infinity=False)),
        "max_tokens": draw(st.one_of(st.none(), st.integers(1, 8192))),
    }
    embedding = {
        "backend": draw(st.sampled_from(["ollama", "sentence-transformers"])),
        "model": draw(st.sampled_from(["embeddinggemma", "nomic-embed-text"])),
        "dimensions": draw(st.one_of(st.none(), st.sampled_from([384, 768, 1024]))),
    }
    database = {
        "backend": "chromadb",
        "mode": draw(st.sampled_from(["persistent", "http"])),
        "host": draw(st.sampled_from(["localhost", "db.internal", "127.0.0.1"])),
        "port": draw(st.integers(1024, 65535)),
        "persist_directory": draw(st.sampled_from(["./chroma_store", "/data/chroma"])),
    }
    paths = {
        "vault": draw(st.sampled_from(["./vault", "/data/vault"])),
        "scratch_dir": draw(st.sampled_from(["./scratch", "/tmp/scratch"])),
        "output_dir": draw(st.sampled_from(["./output", "/data/output"])),
    }
    return {
        "llm": llm,
        "embedding": embedding,
        "database": database,
        "paths": paths,
        # At least the rag/video tool sections (both allowed top-level keys).
        "rag": draw(_tool_section()),
        "video": draw(_tool_section()),
    }


_BASE_SECTIONS = ("llm", "embedding", "database", "paths")


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------

# Feature: project-hardening, Property 4: split-then-merge preserves resolved configuration


@settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
@given(combined=_combined_config())
def test_split_then_merge_preserves_resolved_configuration(
    combined: dict, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Splitting a doc into base(4 sections)+tool file and merging via
    load_config resolves identically to loading the combined doc directly."""
    tmp_path = tmp_path_factory.mktemp("split_merge")

    base_doc = {k: combined[k] for k in _BASE_SECTIONS}
    tool_doc = {k: v for k, v in combined.items() if k not in _BASE_SECTIONS}

    base_file = tmp_path / "base.yaml"
    tool_file = tmp_path / "rag.yaml"
    base_file.write_text(yaml.safe_dump(base_doc), encoding="utf-8")
    tool_file.write_text(yaml.safe_dump(tool_doc), encoding="utf-8")

    merged = load_config(tool_file, base_path=base_file)
    expected = BaseConfig.from_dict(
        {k: dict(v) if isinstance(v, dict) else v for k, v in combined.items()}
    )

    # The four typed sections resolve identically.
    assert merged.llm == expected.llm
    assert merged.embedding == expected.embedding
    assert merged.database == expected.database
    assert merged.paths == expected.paths

    # The unmodeled tool sections are preserved verbatim in raw.
    for section in tool_doc:
        assert merged.raw[section] == combined[section]

    # And the fully merged mapping matches for every top-level section.
    assert merged.raw == expected.raw


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_core_base_file_holds_only_the_four_sections(tmp_path: Path) -> None:
    """A core base file contains exactly the four BaseConfig sections (Req 4.2).

    The shipped local ``configs/base.yaml`` is generated and git-ignored, so
    this validates the core-base contract against a written core file rather
    than the on-disk local copy.
    """
    core = {
        "llm": {"backend": "ollama", "model": "m"},
        "embedding": {"backend": "ollama", "model": "e"},
        "database": {"backend": "chromadb", "mode": "persistent"},
        "paths": {"vault": "./vault"},
    }
    base_file = tmp_path / "base.yaml"
    base_file.write_text(yaml.safe_dump(core), encoding="utf-8")

    config = load_config(base_file, base_path=base_file)
    assert set(config.raw.keys()) == {"llm", "embedding", "database", "paths"}


@pytest.mark.parametrize(
    ("filename", "expected_keys"),
    [
        ("rag.example.yaml", {"rag"}),
        ("video.example.yaml", {"video"}),
        ("generators.example.yaml", {"summaries", "flashcards", "quizzes"}),
        ("orchestrations.example.yaml", {"orchestrations"}),
    ],
)
def test_scoped_file_contains_only_its_own_sections(filename: str, expected_keys: set[str]) -> None:
    """Each scoped config example exposes only its own top-level section(s)."""
    data = yaml.safe_load((CONFIGS_DIR / filename).read_text(encoding="utf-8"))
    assert set(data.keys()) == expected_keys


def test_orchestrations_file_includes_lecture_pipeline_defaults() -> None:
    """The orchestrations scoped example carries lecture_pipeline defaults."""
    data = yaml.safe_load((CONFIGS_DIR / "orchestrations.example.yaml").read_text(encoding="utf-8"))
    assert "lecture_pipeline" in data["orchestrations"]


def test_reference_example_config_loads_without_error() -> None:
    """load_config on the fully-commented reference config succeeds (Req 3.9)."""
    example = CONFIGS_DIR / "base.example.yaml"
    config = load_config(example, base_path=example)
    assert isinstance(config, BaseConfig)
    # The reference documents valid backend enum values.
    assert config.llm.backend == "ollama"


def test_base_only_load_succeeds() -> None:
    """Loading a single base file on its own resolves the typed sections."""
    base_file = CONFIGS_DIR / "base.example.yaml"
    config = load_config(base_file, base_path=base_file)
    assert isinstance(config, BaseConfig)
    assert config.llm.backend == "ollama"
    assert config.embedding.backend == "ollama"
    assert config.database.backend == "chromadb"


def test_missing_tool_file_raises_identifying_path_with_no_partial_merge() -> None:
    """A missing tool file raises an error naming the path; nothing is returned."""
    base_file = CONFIGS_DIR / "base.example.yaml"
    missing = CONFIGS_DIR / "does_not_exist_tool.yaml"

    with pytest.raises(FileNotFoundError) as exc_info:
        load_config(missing, base_path=base_file)

    # The error identifies the offending path.
    assert "does_not_exist_tool" in str(exc_info.value)
