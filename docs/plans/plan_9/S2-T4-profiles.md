# T4: Create Profile-Based Tool Registration — `mcp_server/profiles.py`

**Sprint:** 2 (Parallel with T5)
**Time:** 1.5 hrs
**Prerequisites:** T1 (common.py), T2 (dev.py), T3 (learn.py) must be merged
**Parallel-safe with:** T5 (different files)

---

## Goal

Create the `--profile dev|learn|full` mechanism. A profile determines which tools, resources, and prompts get registered on the FastMCP instance.

---

## Files to Create

| File | Action |
|------|--------|
| `src/mcp_server/profiles.py` | NEW — profile registration logic |
| `tests/unit/test_mcp_profiles.py` | NEW — unit tests |

---

## Design

### Public API

```python
VALID_PROFILES = ("dev", "learn", "full")

def register_dev_tools(mcp: FastMCP, config: BaseConfig, db: DatabaseBackend) -> None:
    """Register developer-focused tools on the MCP server."""

def register_learn_tools(mcp: FastMCP, config: BaseConfig, db: DatabaseBackend) -> None:
    """Register learning-focused tools on the MCP server."""

def register_profile(mcp: FastMCP, profile: str, config: BaseConfig, db: DatabaseBackend) -> None:
    """Register tools for the given profile. Raises ValueError for unknown profiles."""
```

### Profile Contents

| Profile | Tools | Resources | Prompts |
|---------|-------|-----------|---------|
| `dev` | rag_ingest, rag_query, rag_retrieve, store_text, list_collections, collection_info | collections://list, collection://{name} | — |
| `learn` | generate_flashcards, generate_summary, generate_quiz, transcribe_video, clean_transcript | collections://list | study_session_prompt, lecture_processing_prompt |
| `full` | All of the above | All of the above | All of the above |

---

## Implementation Details

### Registration Pattern

Each `register_*` function uses `mcp.tool()` decorator to register functions from `tools/dev.py` or `tools/learn.py`, binding `config` and `db` via closures:

```python
from mcp.server.fastmcp import FastMCP

from config.base import BaseConfig
from db import DatabaseBackend

from .tools import dev as dev_tools
from .tools import learn as learn_tools


def register_dev_tools(mcp: FastMCP, config: BaseConfig, db: DatabaseBackend) -> None:
    """Register developer-focused tools."""

    @mcp.tool()
    def rag_ingest(path: str, collection: str) -> dict:
        """Ingest documents into a RAG collection.

        Args:
            path: Path to file or directory to ingest.
            collection: Collection name to store documents.
        """
        return dev_tools.rag_ingest(path, collection, config, db)

    @mcp.tool()
    def rag_query(collection: str, query: str, top_k: int = 5) -> dict:
        """Query a RAG collection and generate a response.

        Args:
            collection: Collection name to query.
            query: Question or query text.
            top_k: Number of chunks to retrieve (default: 5).
        """
        return dev_tools.rag_query(collection, query, top_k, config, db)

    @mcp.tool()
    def rag_retrieve(collection: str, query: str, top_k: int = 5) -> dict:
        """Retrieve relevant chunks without generating a response.

        Args:
            collection: Collection name to search.
            query: Search query text.
            top_k: Number of chunks to retrieve (default: 5).
        """
        return dev_tools.rag_retrieve(collection, query, top_k, config, db)

    @mcp.tool()
    def store_text(text: str, collection: str, metadata: dict | None = None) -> dict:
        """Store text directly into a RAG collection for later retrieval.

        Use this to persist plans, session summaries, code snippets, or any
        context that should be retrievable across sessions.

        Args:
            text: Text content to store.
            collection: Target collection name.
            metadata: Optional metadata (e.g., {"type": "plan", "project": "myapp"}).
        """
        return dev_tools.store_text(text, collection, config, db, metadata)

    @mcp.tool()
    def list_collections() -> dict:
        """List all available RAG collections."""
        return dev_tools.list_collections(db)

    @mcp.tool()
    def collection_info(collection_name: str) -> dict:
        """Get information about a specific collection.

        Args:
            collection_name: Name of the collection to inspect.
        """
        return dev_tools.collection_info(collection_name, db)

    # Dev resources
    @mcp.resource("collections://list")
    def dev_list_collections_resource() -> str:
        """List all available collections."""
        result = dev_tools.list_collections(db)
        collections = result.get("collections", [])
        return "\n".join(f"- {c}" for c in collections) if collections else "No collections found."

    @mcp.resource("collection://{collection_name}")
    def dev_collection_info_resource(collection_name: str) -> str:
        """Get information about a specific collection."""
        result = dev_tools.collection_info(collection_name, db)
        if result["status"] == "error":
            return f"Error: {result['error']}"
        return f"Collection: {collection_name}\nDocuments: {result.get('document_count', 'unknown')}"


def register_learn_tools(mcp: FastMCP, config: BaseConfig, db: DatabaseBackend) -> None:
    """Register learning-focused tools."""

    @mcp.tool()
    def generate_flashcards(
        collection: str, count: int = 10, difficulty: str = "medium"
    ) -> dict:
        """Generate flashcards from a collection.

        Args:
            collection: Collection containing study material.
            count: Number of flashcards (default: 10).
            difficulty: Difficulty level: easy, medium, hard (default: medium).
        """
        return learn_tools.generate_flashcards(collection, count, difficulty, config, db)

    @mcp.tool()
    def generate_summary(
        collection: str, topic: str | None = None, length: str = "medium"
    ) -> dict:
        """Generate a summary from a collection.

        Args:
            collection: Collection containing material to summarize.
            topic: Optional specific topic to focus on.
            length: Summary length: short, medium, long (default: medium).
        """
        return learn_tools.generate_summary(collection, topic, length, config, db)

    @mcp.tool()
    def generate_quiz(
        collection: str, count: int = 10, question_types: list[str] | None = None
    ) -> dict:
        """Generate a quiz from a collection.

        Args:
            collection: Collection containing quiz material.
            count: Number of questions (default: 10).
            question_types: Types: multiple_choice, true_false, short_answer.
        """
        return learn_tools.generate_quiz(collection, count, question_types, config, db)

    @mcp.tool()
    def transcribe_video(video_path: str, collection: str, model: str = "base") -> dict:
        """Transcribe a video file using Whisper.

        Args:
            video_path: Path to video file.
            collection: Collection to store transcript.
            model: Whisper model: tiny, base, small, medium, large (default: base).
        """
        return learn_tools.transcribe_video(video_path, collection, model, config, db)

    @mcp.tool()
    def clean_transcript(transcript_text: str, model: str | None = None) -> dict:
        """Clean and format a transcript using LLM.

        Args:
            transcript_text: Raw transcript text to clean.
            model: Optional LLM model override.
        """
        return learn_tools.clean_transcript(transcript_text, model, config)

    # Learn resources
    @mcp.resource("collections://list")
    def learn_list_collections_resource() -> str:
        """List all available collections."""
        collections = db.list_collections()
        return "\n".join(f"- {c}" for c in collections) if collections else "No collections."

    # Learn prompts
    @mcp.prompt()
    def study_session_prompt(collection: str, topic: str) -> str:
        """Generate a prompt for a comprehensive study session."""
        return f"""Study the material in collection "{collection}" about "{topic}".

1. generate_summary(collection="{collection}", topic="{topic}")
2. generate_flashcards(collection="{collection}", count=15)
3. generate_quiz(collection="{collection}", count=10)"""

    @mcp.prompt()
    def lecture_processing_prompt(video_path: str, course: str) -> str:
        """Generate a prompt for processing a lecture video."""
        return f"""Process lecture video "{video_path}" for course "{course}".

1. transcribe_video(video_path="{video_path}", collection="{course}")
2. clean_transcript() on the result
3. Generate study materials from the transcript"""


def register_profile(
    mcp: FastMCP, profile: str, config: BaseConfig, db: DatabaseBackend
) -> None:
    """Register tools for the given profile.

    Args:
        mcp: FastMCP server instance.
        profile: One of "dev", "learn", "full".
        config: Base configuration.
        db: Database backend.

    Raises:
        ValueError: If profile is not recognized.
    """
    if profile not in VALID_PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Valid: {VALID_PROFILES}")

    if profile in ("dev", "full"):
        register_dev_tools(mcp, config, db)
    if profile in ("learn", "full"):
        register_learn_tools(mcp, config, db)
```

---

## Tests

### `tests/unit/test_mcp_profiles.py`

```python
"""Tests for mcp_server.profiles — profile-based tool registration."""

import asyncio

import pytest
import yaml

from mcp.server.fastmcp import FastMCP


@pytest.fixture()
def profile_config(tmp_path):
    cfg = {
        "llm": {"model": "test"},
        "database": {"mode": "persistent", "persist_directory": str(tmp_path / "chroma")},
    }
    path = tmp_path / "base.yaml"
    path.write_text(yaml.dump(cfg))
    return str(path)


def _get_tool_names(mcp):
    return [t.name for t in asyncio.run(mcp.list_tools())]


class TestRegisterProfile:
    def test_dev_profile_has_rag_tools(self, profile_config):
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.profiles import register_profile

        config = load_config(profile_config)
        db = ChromaDBBackend(config.database)
        mcp = FastMCP("test")
        register_profile(mcp, "dev", config, db)

        names = _get_tool_names(mcp)
        assert "rag_query" in names
        assert "store_text" in names
        assert "list_collections" in names
        # Should NOT have learn tools
        assert "generate_flashcards" not in names

    def test_learn_profile_has_flashcard_tools(self, profile_config):
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.profiles import register_profile

        config = load_config(profile_config)
        db = ChromaDBBackend(config.database)
        mcp = FastMCP("test")
        register_profile(mcp, "learn", config, db)

        names = _get_tool_names(mcp)
        assert "generate_flashcards" in names
        # Should NOT have dev tools
        assert "rag_query" not in names
        assert "store_text" not in names

    def test_full_profile_has_everything(self, profile_config):
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.profiles import register_profile

        config = load_config(profile_config)
        db = ChromaDBBackend(config.database)
        mcp = FastMCP("test")
        register_profile(mcp, "full", config, db)

        names = _get_tool_names(mcp)
        assert "rag_query" in names
        assert "store_text" in names
        assert "generate_flashcards" in names

    def test_invalid_profile_raises(self, profile_config):
        from config import load_config
        from db import ChromaDBBackend
        from mcp_server.profiles import register_profile

        config = load_config(profile_config)
        db = ChromaDBBackend(config.database)
        mcp = FastMCP("test")
        with pytest.raises(ValueError, match="Unknown profile"):
            register_profile(mcp, "invalid", config, db)
```

---

## Session Prompt

```
I'm implementing Plan 9, Task T4 from docs/plans/plan_9/S2-T4-profiles.md.

Goal: Create mcp_server/profiles.py with profile-based tool registration.

Please:
1. Read docs/plans/plan_9/S2-T4-profiles.md completely
2. Read the newly created src/mcp_server/tools/dev.py and src/mcp_server/tools/learn.py
3. Create src/mcp_server/profiles.py with register_dev_tools, register_learn_tools, register_profile
4. Each register function wraps tool functions with mcp.tool() decorators, binding config+db via closures
5. Create tests/unit/test_mcp_profiles.py
6. Run tests and fix issues

The key pattern: profiles.py is the ONLY place where mcp.tool() decorators are applied.
The tools/dev.py and tools/learn.py functions are plain functions — profiles.py wraps them.
```

---

## Verification

```bash
pytest tests/unit/test_mcp_profiles.py -v

python -c "
from mcp.server.fastmcp import FastMCP
from mcp_server.profiles import VALID_PROFILES
assert 'dev' in VALID_PROFILES
assert 'learn' in VALID_PROFILES
assert 'full' in VALID_PROFILES
print('PASS')
"
```

---

## Done When

- [ ] `src/mcp_server/profiles.py` exists with all 3 public functions
- [ ] `dev` profile registers only RAG + store_text + collection tools
- [ ] `learn` profile registers only flashcard/summary/quiz/video tools
- [ ] `full` profile registers everything
- [ ] `tests/unit/test_mcp_profiles.py` passes
- [ ] Existing tests still pass
