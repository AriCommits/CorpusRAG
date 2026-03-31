"""Simple smoke test for local ingest + query flow.

Run:
    python3 tests/test_smoke.py

Optional environment variables:
    TEST_COLLECTION (default: "test")
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from corpus_callosum.agent import RagAgent
from corpus_callosum.ingest import Ingester


def main() -> None:
    collection = os.getenv("TEST_COLLECTION", "test")

    with tempfile.TemporaryDirectory(prefix="corpus_smoke_") as temp_dir:
        sample_path = Path(temp_dir) / "sample.md"
        sample_path.write_text(
            """
# CorpusCallosum Smoke Test

This document is about hybrid retrieval.
It combines semantic search with BM25 keyword search.
The goal is better recall and precision for student questions.
""".strip()
            + "\n",
            encoding="utf-8",
        )

        ingester = Ingester()
        result = ingester.ingest_path(sample_path, collection)
        print(
            f"Indexed {result.chunks_indexed} chunks from {result.files_indexed} file(s) into '{collection}'."
        )

    agent = RagAgent()
    stream, chunks = agent.query(
        query="what is the main topic of this document?",
        collection_name=collection,
    )

    print(f"Retrieved {len(chunks)} chunk(s).")
    print("Answer:")
    print("".join(stream).strip())


if __name__ == "__main__":
    main()
