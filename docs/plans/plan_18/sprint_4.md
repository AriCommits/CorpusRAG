# Sprint 4 — Export Metadata, Collections in RAG TUI

**Plan:** docs/plans/plan_18/OVERVIEW.md
**Wave:** 4 of 6
**Can run in parallel with:** none — depends on Sprint 3
**Must complete before:** Sprint 5

---

## Agents in This Wave

### Agent A: C8 — Store Embedding Model in Export Metadata

**Complexity:** S
**Estimated time:** 1.5 hours
**Files to modify:**
- `src/db/management.py` — include `embedding_model` field in export/backup JSON output
- `src/tools/rag/ingest.py` — store embedding model name in collection metadata during ingestion

**Depends on:** C6, C7 (management.py stabilized)
**Blocks:** C13 (ingest.py)

**Instructions:**
In `src/tools/rag/ingest.py`, when creating or updating a collection during ingestion, store the embedding model name in the collection's metadata:
```python
metadata["embedding_model"] = cfg.embedding.model
```

In `src/db/management.py`'s `export_collection` method, read the collection metadata and include it as a top-level field in the export JSON:
```python
export_wrapper = {
    "collection_name": collection_name,
    "embedding_model": collection_metadata.get("embedding_model", "unknown"),
    "export_timestamp": datetime.now().isoformat(),
    "total_documents": len(export_data),
    "data": export_data,
}
```

Similarly update `backup_collection` to include this field in the backup JSON.

**Definition of Done:**
- [ ] Export JSON contains `embedding_model` field
- [ ] Backup JSON contains `embedding_model` field
- [ ] After ingesting, collection metadata includes `embedding_model`
- [ ] No regressions in existing tests

---

### Agent B: C14 — Add Collections Management to RAG TUI

**Complexity:** S
**Estimated time:** 1 hour
**Files to modify:**
- `src/tools/rag/tui.py` — add `/collections` slash command or keybinding to open collections manager

**Depends on:** C10 (collection switching), C12 (TUI exit fix)
**Blocks:** D1

**Instructions:**
Add a `/collections` slash command to the RAG TUI that opens the `CollectionManagerScreen` as a modal or pushed screen. This allows users to manage collections (list, delete, view info) without exiting the RAG TUI. Use Textual's `push_screen` to show the collections manager and `pop_screen` to return.

Also consider adding a keybinding (e.g., `ctrl+o`) that does the same thing.

The collections manager screen (`tui_collections.py`) should already work as a standalone screen — just push it onto the screen stack.

**Definition of Done:**
- [ ] `/collections` command in RAG TUI opens the collections manager
- [ ] User can return to RAG chat after closing collections manager
- [ ] Keybinding (ctrl+o or similar) also opens collections manager
- [ ] No regressions in existing tests
