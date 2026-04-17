"""RAG retrieval logic using parent-child retrieval architecture."""

from dataclasses import dataclass
from typing import Any

from db import DatabaseBackend

from .config import RAGConfig
from .embeddings import EmbeddingClient
from .storage import LocalFileStore


@dataclass(frozen=True)
class RetrievedDocument:
    """A retrieved parent document."""

    id: str
    text: str
    metadata: dict[str, Any]
    rank: int
    score: float = 0.0


class RAGRetriever:
    """Retrieve relevant documents for RAG using parent-child architecture."""

    def __init__(self, config: RAGConfig, db: DatabaseBackend):
        """Initialize RAG retriever.

        Args:
            config: RAG configuration
            db: Database backend
        """
        self.config = config
        self.db = db
        self.embedder = EmbeddingClient(config)

        # Initialize parent document store
        self.config.parent_store.path.mkdir(parents=True, exist_ok=True)
        self.parent_store = LocalFileStore(str(self.config.parent_store.path))

    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Retrieve parent documents using child document search.

        Uses parent-child retrieval: searches for child chunks in vector store,
        then retrieves full parent documents from document store based on
        parent_id metadata in child chunks.

        Args:
            query: Search query
            collection: Collection name
            top_k: Number of parent documents to retrieve (uses config default if None)
            where: Metadata filter dict for filtering on tags, sections, etc.

        Returns:
            List of retrieved parent documents
        """
        if top_k is None:
            top_k = self.config.retrieval.top_k_final

        # Get full collection name with prefix
        full_collection = f"{self.config.collection_prefix}_{collection}"

        # Check if collection exists
        if not self.db.collection_exists(full_collection):
            return []

        # Embed the query
        query_embedding = self.embedder.embed_query(query)

        # Search child documents with optional metadata filtering
        results = self.db.query(
            full_collection,
            query_embedding=query_embedding,
            n_results=top_k * 3,  # Over-fetch to account for duplicate parents
            where=where,
        )

        # Track unique parent IDs to avoid duplicates
        parent_ids_seen = set()
        retrieved_docs = []
        rank = 1

        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, child_id in enumerate(ids):
            metadata = metadatas[i] if i < len(metadatas) else {}
            parent_id = metadata.get("parent_id")

            # Skip if we've already retrieved this parent
            if parent_id in parent_ids_seen:
                continue

            parent_ids_seen.add(parent_id)

            # Retrieve parent document from store
            if parent_id:
                try:
                    parent_doc = self.parent_store.mget([parent_id])
                    if parent_doc and parent_doc[0]:
                        parent_langchain_doc = parent_doc[0]
                        distance = distances[i] if i < len(distances) else 0.0
                        retrieved_docs.append(
                            RetrievedDocument(
                                id=parent_id,
                                text=parent_langchain_doc.page_content,
                                metadata=parent_langchain_doc.metadata or {},
                                rank=rank,
                                score=1.0 / (1.0 + distance),
                            )
                        )
                        rank += 1

                        # Stop once we have enough parent documents
                        if len(retrieved_docs) >= top_k:
                            break
                except Exception:
                    # Skip if parent document cannot be retrieved
                    continue

        return retrieved_docs
