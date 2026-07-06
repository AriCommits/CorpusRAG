"""Live end-to-end RAG pipeline test."""

import pytest

pytestmark = pytest.mark.live

TEST_COLLECTION = "_test_live_rag"


@pytest.fixture
def test_doc(tmp_path):
    doc = tmp_path / "test_notes.md"
    doc.write_text(
        "# Photosynthesis\n\n"
        "Photosynthesis is the process by which plants convert sunlight into energy.\n"
        "It occurs in the chloroplasts and produces glucose and oxygen.\n\n"
        "## Light Reactions\n\n"
        "The light reactions occur in the thylakoid membranes.\n"
    )
    return doc


def test_ingest_and_query(live_config, live_db, test_doc):
    """Full pipeline: ingest a file, query it, verify results."""
    from tools.rag import RAGConfig, RAGIngester, RAGRetriever

    rag_config = RAGConfig.from_dict(live_config.to_dict())

    full_name = f"{rag_config.collection_prefix}_{TEST_COLLECTION}"
    if live_db.collection_exists(full_name):
        live_db.delete_collection(full_name)

    try:
        ingester = RAGIngester(rag_config, live_db)
        result = ingester.ingest_path(str(test_doc.parent), TEST_COLLECTION)
        assert result.files_indexed >= 1
        assert result.chunks_indexed >= 1

        retriever = RAGRetriever(rag_config, live_db)
        docs = retriever.retrieve("What is photosynthesis?", TEST_COLLECTION, top_k=3)
        assert len(docs) > 0
        assert any("photosynthesis" in d.text.lower() for d in docs)
    finally:
        if live_db.collection_exists(full_name):
            live_db.delete_collection(full_name)
