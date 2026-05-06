# Sprint 1 — Leaf Modules & Scaffolding

**Plan:** docs/plans/plan_16/handwriting_ingest_spec.md
**Wave:** 1 of 4
**Can run in parallel with:** all agents in this wave (H1, H2, H3, H4, H8)
**Must complete before:** Sprint 2 (H5 needs H1's `DiscoveredImage`)

---

## Agents in This Wave

### Agent A: H1 — Recursive Directory Walker

**Complexity:** S
**Estimated time:** 1.5 h
**Files to modify:**
- `src/tools/handwriting/walker.py` (NEW) — implement `walk_directory`, `filter_already_ingested`, `_hash_file`, and the `DiscoveredImage` dataclass exactly as specified in spec §Step 1.
- `tests/tools/handwriting/test_walker.py` (NEW) — test recursive vs non-recursive walk, extension filtering, hash determinism, dedup filtering.

**Depends on:** none
**Blocks:** H5, H6

**Instructions:**
Implement `walker.py` per spec §Step 1. Key points:
- `SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}` — case-insensitive matching via `suffix.lower()`.
- `walk_directory` returns sorted list (path-sorted for deterministic ordering across runs).
- `_hash_file` reads in 64 KiB chunks (don't load whole file into memory).
- `filter_already_ingested` returns `(new_images, skipped_count)` tuple.
- Per spec Open Question #5: add a `max_depth: int | None = None` parameter; when set, limit recursion depth (compute via `len(path.relative_to(root).parts) - 1` for files).
- Per spec Open Question #4: TIFF normalization is acknowledged to live in preprocessor — don't do it here.

**Definition of Done:**
- [ ] `walk_directory` returns `DiscoveredImage` objects with correct `folder_hierarchy` (folders only, no filename).
- [ ] `_hash_file` produces stable SHA-256 across re-runs.
- [ ] `--max-depth` semantics correct (depth 0 = root only).
- [ ] `filter_already_ingested` correctly partitions by hash membership.
- [ ] Tests pass; uses tmp_path fixture with synthetic image files.

---

### Agent B: H2 — Image Preprocessor

**Complexity:** S
**Estimated time:** 1.5 h
**Files to modify:**
- `src/tools/handwriting/preprocessor.py` (NEW) — `preprocess_image`, `is_likely_blank` per spec §Step 2.
- `tests/tools/handwriting/test_preprocessor.py` (NEW) — test upscale logic, blank detection, no-op path when image is already large enough and flags are off.

**Depends on:** none
**Blocks:** H6 (orchestrator)

**Instructions:**
Implement `preprocessor.py` per spec §Step 2. Key points:
- `preprocess_image` returns the **original path unchanged** if no preprocessing was needed (don't write a file just to copy it).
- Output path uses `image_path.with_stem(image_path.stem + "_processed")`. Save with quality=92.
- Per spec Open Question #4: add TIFF normalization — if `image_path.suffix.lower() in {".tif", ".tiff"}`, force re-save as JPEG (mark `modified = True`).
- `is_likely_blank` uses edge density (mean absolute first-difference along both axes) ÷ 255 < threshold (default 0.02).
- Use Pillow + numpy. Convert to "L" (grayscale) for blank detection, "RGB" for the preprocessing output.

**Definition of Done:**
- [ ] Returns original path when no modifications applied.
- [ ] Upscales when `img.width < target_width` using LANCZOS; preserves aspect ratio.
- [ ] TIFF inputs always normalized to JPEG.
- [ ] `is_likely_blank` returns True for solid-color images, False for an image with text-like structure.
- [ ] Tests use synthetic PIL images (no fixture files required).

---

### Agent C: H3 — Vision OCR

**Complexity:** S
**Estimated time:** 1 h
**Files to modify:**
- `src/tools/handwriting/ocr.py` (NEW) — `ocr_handwriting` and `HANDWRITING_PROMPT` constant per spec §Step 3.
- `tests/tools/handwriting/test_ocr.py` (NEW) — mock `ollama.chat`; verify prompt content, base64 encoding, and return-string stripping.

**Depends on:** none
**Blocks:** H6 (orchestrator)

**Instructions:**
Implement `ocr.py` per spec §Step 3. Key points:
- Use `ollama.chat(model=model, messages=[{"role": "user", "content": HANDWRITING_PROMPT, "images": [image_b64]}])`.
- Read image bytes once and base64-encode.
- Return `response["message"]["content"].strip()`.
- Keep the prompt verbatim from the spec — it is the contract for the correction pass.
- Use `monkeypatch` / `unittest.mock` to stub `ollama.chat` in tests; don't require Ollama running.

**Definition of Done:**
- [ ] `HANDWRITING_PROMPT` matches spec exactly (keep `[BLANK_PAGE]`, `[illegible]`, `[Diagram: ...]` markers — they are consumed downstream).
- [ ] Function signature: `ocr_handwriting(image_path: Path, model: str = "llava") -> str`.
- [ ] Tests verify `ollama.chat` is called with base64-encoded image bytes.

---

### Agent D: H4 — LLM Correction Pass

**Complexity:** S
**Estimated time:** 1 h
**Files to modify:**
- `src/tools/handwriting/corrector.py` (NEW) — `correct_ocr_output`, `estimate_correction_confidence`, `CORRECTION_PROMPT` per spec §Step 4.
- `tests/tools/handwriting/test_corrector.py` (NEW) — mock `ollama.generate`; verify `[BLANK_PAGE]` short-circuit; confidence-score math.

**Depends on:** none
**Blocks:** H6 (orchestrator)

**Instructions:**
Implement `corrector.py` per spec §Step 4. Key points:
- Default model: `mistral` (NOT llava — spec is explicit on this for performance).
- Short-circuit: if input is exactly `"[BLANK_PAGE]"` (after strip) or empty, return it unchanged without calling the LLM.
- `estimate_correction_confidence`: word-set overlap `len(raw ∩ corrected) / len(raw)`. Returns 0.0 when raw is empty/whitespace; 1.0 when raw words are a subset of corrected.
- Lowercase before comparing.

**Definition of Done:**
- [ ] `correct_ocr_output("[BLANK_PAGE]")` returns `"[BLANK_PAGE]"` without invoking ollama (verifiable via mock not-called assertion).
- [ ] Confidence = 1.0 when raw == corrected; < 1.0 when corrected omits raw words.
- [ ] Confidence handles empty/whitespace input gracefully (no division by zero).
- [ ] Prompt matches spec verbatim.

---

### Agent E: H8 — Package Scaffolding & Dependencies

**Complexity:** S
**Estimated time:** 0.5 h
**Files to modify:**
- `src/tools/handwriting/__init__.py` (NEW) — empty file (or package docstring only). Do NOT eagerly import sibling modules to avoid circular imports during Wave 1 dev.
- `tests/tools/handwriting/__init__.py` (NEW) — empty.
- `pyproject.toml` — add `[handwriting]` optional extras group with `ollama>=0.1.0`, `Pillow>=10.0.0`, `numpy>=1.24.0` (per spec §Dependencies).
- `README.md` — append a "Handwriting Ingestion" section under existing tools docs: install command (`pip install corpusrag[handwriting]`), required `ollama pull` calls, one-liner CLI example.

**Depends on:** none
**Blocks:** none (purely additive scaffolding)

**Instructions:**
- Find existing `[project.optional-dependencies]` table in `pyproject.toml`. If it doesn't exist, create it. Add only the `handwriting` group; do not modify other groups.
- Match the README's existing tone and section style. Keep it short — under 30 lines.
- The CLI command (`corpus handwriting ingest …`) won't be runnable until Sprint 4; that's fine — the docs anticipate it.

**Definition of Done:**
- [ ] `pip install -e .[handwriting]` resolves cleanly.
- [ ] `pyproject.toml` is valid TOML (run `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`).
- [ ] README has a Handwriting Ingestion section with install + model pull commands.
- [ ] Empty `__init__.py` files exist so pytest can discover tests in the next sprints.
