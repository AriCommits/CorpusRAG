"""Live tests for ChromaDB connectivity."""

import pytest

pytestmark = pytest.mark.live

TEST_COLLECTION = "_test_live_probe"


def test_chromadb_heartbeat(live_config):
    import httpx

    host = live_config.database.host
    port = live_config.database.port
    try:
        r = httpx.get(f"http://{host}:{port}/api/v2/heartbeat", timeout=5)
    except httpx.ConnectError:
        pytest.skip(f"ChromaDB not reachable at {host}:{port}")
    assert r.status_code == 200


def test_list_collections(live_db):
    collections = live_db.list_collections()
    assert isinstance(collections, list)


def test_create_and_delete_collection(live_db):
    if live_db.collection_exists(TEST_COLLECTION):
        live_db.delete_collection(TEST_COLLECTION)
    live_db.create_collection(TEST_COLLECTION)
    assert live_db.collection_exists(TEST_COLLECTION)
    live_db.delete_collection(TEST_COLLECTION)
    assert not live_db.collection_exists(TEST_COLLECTION)


def test_add_and_query_document(live_db, live_config):
    """Add a document with a real embedding and query it back."""
    from tools.rag.config import RAGConfig
    from tools.rag.pipeline import EmbeddingClient

    rag_config = RAGConfig.from_dict(live_config.to_dict())
    embedder = EmbeddingClient(rag_config)

    collection = TEST_COLLECTION
    if live_db.collection_exists(collection):
        live_db.delete_collection(collection)
    live_db.create_collection(collection)

    try:
        text = "The mitochondria is the powerhouse of the cell."
        embedding = embedder.embed_texts([text])[0]
        assert len(embedding) > 0

        live_db.add_documents(
            collection=collection,
            documents=[text],
            embeddings=[embedding],
            metadata=[{"source": "test"}],
            ids=["test_doc_1"],
        )

        results = live_db.query(collection, embedding, n_results=1)
        assert len(results["ids"][0]) > 0
        assert "mitochondria" in results["documents"][0][0].lower()
    finally:
        live_db.delete_collection(collection)
