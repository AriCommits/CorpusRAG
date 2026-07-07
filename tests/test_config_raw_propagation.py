"""Tests for BaseConfig.raw propagation and deep-merge semantics."""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from config.base import BaseConfig
from config.loader import deep_merge

# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def _sample_config() -> dict:
    return {
        "llm": {
            "endpoint": "http://localhost:11434",
            "model": "gemma4:26b",
            "api_key": "super-secret-value",
        },
        "embedding": {"backend": "ollama", "model": "embeddinggemma"},
        "database": {"backend": "chromadb", "host": "localhost", "port": 8000},
        "paths": {"vault": "./vault"},
        # Unmodeled sections that should still be retained in `raw`.
        "rag": {"child_chunk_size": 512, "child_chunk_overlap": 64},
        "tools": {"enabled": ["summaries", "quizzes"]},
    }


def test_from_dict_retains_full_raw_dict():
    """`raw` should equal the exact dictionary passed to from_dict."""
    sample = _sample_config()
    config = BaseConfig.from_dict(sample)

    assert config.raw == sample
    # Unmodeled sections are preserved verbatim in raw.
    assert config.raw["rag"] == {"child_chunk_size": 512, "child_chunk_overlap": 64}
    assert config.raw["tools"] == {"enabled": ["summaries", "quizzes"]}


def test_to_dict_unchanged_only_four_sections_and_masks_api_key():
    """to_dict() must emit only the four modeled sections and mask api_key."""
    sample = _sample_config()
    config = BaseConfig.from_dict(sample)

    result = config.to_dict()

    assert set(result.keys()) == {"llm", "embedding", "database", "paths"}
    # Secret must be masked, not leaked.
    assert result["llm"]["api_key"] == "***"
    assert result["llm"]["api_key"] != "super-secret-value"
    # Unmodeled sections must not appear in to_dict output.
    assert "rag" not in result
    assert "tools" not in result


def test_to_dict_masks_none_api_key_as_none():
    """When no api_key is set, to_dict should emit None (not '***')."""
    config = BaseConfig.from_dict({"llm": {"model": "gemma4:26b"}})
    assert config.to_dict()["llm"]["api_key"] is None


def test_raw_is_excluded_from_equality():
    """Two configs with identical modeled fields but different raw compare equal."""
    modeled = {
        "llm": {"model": "gemma4:26b"},
        "embedding": {"model": "embeddinggemma"},
        "database": {"host": "localhost"},
        "paths": {"vault": "./vault"},
    }

    a_data = dict(modeled)
    a_data["rag"] = {"child_chunk_size": 128}

    b_data = dict(modeled)
    b_data["rag"] = {"child_chunk_size": 999, "extra": "different"}

    config_a = BaseConfig.from_dict(a_data)
    config_b = BaseConfig.from_dict(b_data)

    # raw differs...
    assert config_a.raw != config_b.raw
    # ...but the configs are equal because raw is compare=False.
    assert config_a == config_b


def test_raw_is_excluded_from_repr():
    """raw (repr=False) should not leak into the repr output."""
    config = BaseConfig.from_dict(_sample_config())
    # The unmodeled `rag`/`tools` sections live only in `raw`; since raw is
    # repr=False, they must not surface in the repr.
    rendered = repr(config)
    assert "raw=" not in rendered
    assert "child_chunk_size" not in rendered


# ---------------------------------------------------------------------------
# Property-based test
# ---------------------------------------------------------------------------

# Feature: project-hardening, Property 3: deep-merge override and retention semantics


def _nested_dicts(max_depth: int):
    """Strategy producing JSON-like nested dicts up to a bounded depth."""
    keys = st.sampled_from(["a", "b", "c", "d", "e"])
    scalars = st.one_of(
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
        st.text(max_size=8),
        st.none(),
    )

    def extend(children):
        return st.dictionaries(keys, st.one_of(scalars, children), max_size=4)

    return st.recursive(
        st.dictionaries(keys, scalars, max_size=4),
        extend,
        max_leaves=max_depth,
    )


@settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
@given(base=_nested_dicts(max_depth=5), override=_nested_dicts(max_depth=5))
def test_deep_merge_override_and_retention_semantics(base, override):
    """deep_merge retains base-only keys, override wins on conflict, mappings recurse."""
    result = deep_merge(base, override)

    # (a) Keys only in base are retained with their original values.
    for key in base:
        if key not in override:
            assert key in result
            assert result[key] == base[key]

    # All override keys must be present.
    for key in override:
        assert key in result

    for key, override_value in override.items():
        base_value = base.get(key, "__missing__")
        result_value = result[key]

        if key in base and isinstance(base_value, dict) and isinstance(override_value, dict):
            # (c) When both values are mappings, result equals recursive deep_merge.
            assert result_value == deep_merge(base_value, override_value)
        else:
            # (b) Scalar or type-conflicting keys: override wins.
            assert result_value == override_value
