# Sprint 3 — Docs Match the Live CLI

**Plan:** docs/plans/plan_21/OVERVIEW.md
**Wave:** 3 of 4
**Can run in parallel with:** none — serial
**Must complete before:** Sprint 4 (V1)

Branch from post-Wave-2 `main`. Do not start until S1, S2, and S4 are merged
(so the docs describe the simplified architecture, not the pre-dedup one).

---

## Agents in This Wave

### Agent A: DOC1 — Rewrite stale architecture docs to the live CLI

**Complexity:** M
**Estimated time:** 3 hours
**Files to modify:**
- `docs/architecture.md`
- `docs/tools-usage.md`
- `docs/mcp-integration.md`
- `docs/docker-deployment.md`
- `docs/troubleshooting.md`
- `docs/configuration.md` — collection-prefix table and remaining CorpusCallosum / dead-knob text only.

**Depends on:** C1, C2, C5, S1, S2, S4
**Blocks:** V1

**Instructions:**
These six files still describe **CorpusCallosum**, standalone `corpus-rag` /
`corpus-flashcards` / `corpus-db` binaries, auto-exposed MCP tools,
`study_session` / `knowledge_base`, `config/schema.py`, and
`collection://{name}`. Plan 20 already fixed README, `src/CLI.md`, and
`cli.txt` — treat those plus `src/cli.py` as the source of truth.

Required content:

1. Product name **CorpusRAG** everywhere in these files.
2. Command tree from the live Click group:
   `corpus setup|doctor|benchmark|tools|db|collections|dev|orchestrate`.
   Nested: `corpus tools rag|video|handwriting|summaries|learning`.
   Orchestrate: `lecture-pipeline` only.
3. Collection namespace: one table, `rag_<name>` for RAG **and** study
   generators. Do not document `flashcards_*` / `summaries_*` /
   `quizzes_*` as separate stores.
4. MCP: **manual** subset. Include a table:

   | Capability | CLI | MCP |
   |---|---|---|
   | ingest / query / retrieve | `corpus tools rag …` | `rag_ingest`, `rag_query`, `rag_retrieve` |
   | store_text | — | `store_text` |
   | flashcards / summary / quiz | `corpus tools learning …` / `summaries` | `generate_*` |
   | handwriting | `corpus tools handwriting …` | CLI-only |
   | lecture pipeline | `corpus orchestrate lecture-pipeline` | CLI-only |
   | TUI / sync / chat | CLI | CLI-only |
   | db backup | `corpus db` | CLI-only |

5. Delete or rewrite sections that mention `schema.py`,
   `StudySessionOrchestrator`, `KnowledgeBaseOrchestrator`,
   `lecture_processing_prompt`, `collections://` resources other than
   `collections://list`, and “all CLI tools automatically available via
   MCP”.
6. Retrieval: hybrid/semantic/keyword as **names of one staged
   pipeline**, not three independent codebases. Parent store is per
   collection.
7. Docker / troubleshooting examples must use `corpus tools rag ingest`
   (not `corpus-rag ingest`) and the compose paths that actually exist.

Do **not** edit `docs/phases/` or `docs/plans/plan_*`. Do **not** edit
`src/cli.py`, `setup_wizard.py`, README, or `src/CLI.md`.

Grep the six files for `CorpusCallosum`, `corpus-rag`, `corpus-flashcards`,
`study.session`, `schema.py` and drive that count to zero.

**Definition of Done:**
- [ ] No CorpusCallosum / standalone `corpus-rag` / `schema.py` /
      `study_session` / auto-MCP claims in the six files.
- [ ] Collection table is `rag_<name>` only.
- [ ] MCP documented as a manual, partial adapter with a CLI↔MCP table.
- [ ] Examples use `corpus tools …` and `corpus orchestrate lecture-pipeline`.
- [ ] Tests written and passing for modified files (docs-only; no new
      runtime tests required unless you extend CLI-docs consistency).
- [ ] No regressions in existing tests.

---

## What this wave unblocks

Sprint 4 verification can treat docs and code as one story.
