# Sprint 5 — Ingest Path Storage & Sync Default

**Plan:** docs/plans/plan_18/OVERVIEW.md
**Wave:** 5 of 6
**Can run in parallel with:** none — depends on Sprint 4
**Must complete before:** Sprint 6

---

## Agents in This Wave

### Agent A: C13 — Store Ingest Path in Collection Metadata + `sync` Default Path

**Complexity:** M
**Estimated time:** 2 hours
**Files to modify:**
- `src/tools/rag/ingest.py` — store resolved ingest path in collection metadata
- `src/tools/rag/cli.py` — make `sync` path argument optional, read from metadata if missing
- `src/db/collections_cli.py` — add `update-path` command

**Depends on:** C8 (ingest.py modified), C9 (rag/cli.py modified), C4 (collections_cli.py fixed)
**Blocks:** D1

**Instructions:**

**Ingest path storage:** In `src/tools/rag/ingest.py`, after successful ingestion, store the resolved absolute path in the collection's metadata:
```python
collection_metadata["ingest_source_path"] = str(Path(path).resolve())
```
Use ChromaDB's collection `modify()` to update metadata, or store it during collection creation.

**Sync default path:** In `src/tools/rag/cli.py`, change the `sync` command's `path` argument from required to optional. If not provided, read `ingest_source_path` from the collection's metadata. If neither is available, error with a helpful message.

```python
@rag.command()
@click.argument("path", type=click.Path(exists=True), required=False)
@click.option("--collection", "-c", required=True, help="Collection name")
...
def sync(path: str | None, collection: str, ...):
    if path is None:
        # Read from collection metadata
        stats = db.get_collection_stats(collection)
        path = stats.get("metadata", {}).get("ingest_source_path")
        if not path:
            raise click.UsageError("No path provided and no stored ingest path found. ...")
```

**Update-path command:** In `src/db/collections_cli.py`, add:
```python
@collections_cmd.command(name="update-path")
@click.argument("name")
@click.argument("path", type=click.Path(exists=True))
def update_path(name, path, config):
    """Update the stored ingest source path for a collection."""
```

**Definition of Done:**
- [ ] After `corpus rag ingest ./docs -c notes`, collection metadata contains `ingest_source_path`
- [ ] `corpus rag sync -c notes` (no path) uses stored path
- [ ] `corpus rag sync ./new-path -c notes` overrides and updates stored path
- [ ] `corpus collections update-path notes ./new-docs` updates the stored path
- [ ] Error message is clear when no path is available
- [ ] No regressions in existing tests
