"""
Knowledge Base Orchestrator.

Builds and manages knowledge bases from document collections.
"""

from pathlib import Path
from typing import Any

from corpus_callosum.config import BaseConfig
from corpus_callosum.db import DatabaseBackend
from corpus_callosum.tools.rag import RAGAgent, RAGConfig, RAGIngester, RAGRetriever


class KnowledgeBaseOrchestrator:
    """
    Orchestrates knowledge base building and querying.
    
    Workflow:
    1. Ingest documents from various sources
    2. Index into collections
    3. Provide unified query interface
    """
    
    def __init__(self, config: BaseConfig, db: DatabaseBackend):
        """
        Initialize the knowledge base orchestrator.
        
        Args:
            config: Base configuration
            db: Database backend instance
        """
        self.config = config
        self.db = db
        
        # Initialize RAG config
        self.rag_config = RAGConfig.from_dict(config.to_dict())
    
    def build_knowledge_base(
        self,
        source_path: Path,
        collection: str,
        recursive: bool = True,
    ) -> dict[str, Any]:
        """
        Build a knowledge base from a document source.
        
        Args:
            source_path: Path to document(s) to ingest
            collection: Collection name
            recursive: Process subdirectories recursively
        
        Returns:
            Ingestion statistics
        """
        ingester = RAGIngester(self.rag_config, self.db)
        
        # Ingest documents
        result = ingester.ingest_path(source_path, collection)
        
        return {
            "collection": collection,
            "source": str(source_path),
            "documents_processed": result.documents_processed,
            "chunks_created": result.chunks_created,
            "status": "success",
        }
    
    def query_knowledge_base(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        generate_response: bool = True,
    ) -> dict[str, Any]:
        """
        Query a knowledge base.
        
        Args:
            collection: Collection to query
            query: Query string
            top_k: Number of chunks to retrieve
            generate_response: Generate LLM response (vs just retrieve chunks)
        
        Returns:
            Query results with chunks and optional response
        """
        if generate_response:
            agent = RAGAgent(self.rag_config, self.db)
            response = agent.query(collection, query)
            
            return {
                "collection": collection,
                "query": query,
                "response": response,
            }
        else:
            retriever = RAGRetriever(self.rag_config, self.db)
            chunks = retriever.retrieve(collection, query, top_k=top_k)
            
            return {
                "collection": collection,
                "query": query,
                "chunks": [
                    {
                        "text": chunk.text,
                        "source": chunk.metadata.get("source", ""),
                        "score": chunk.score,
                    }
                    for chunk in chunks
                ],
            }
    
    def merge_collections(
        self,
        source_collections: list[str],
        target_collection: str,
    ) -> dict[str, Any]:
        """
        Merge multiple collections into one.
        
        Args:
            source_collections: Collections to merge
            target_collection: Target collection name
        
        Returns:
            Merge statistics
        """
        total_documents = 0
        
        for source in source_collections:
            # Get source collection
            source_col = self.db.get_collection(source)
            
            # Get all documents from source
            results = source_col.get()
            
            # Add to target collection
            target_col = self.db.get_collection(target_collection)
            
            if results["ids"]:
                target_col.add(
                    ids=results["ids"],
                    documents=results["documents"],
                    metadatas=results["metadatas"],
                    embeddings=results.get("embeddings"),
                )
                total_documents += len(results["ids"])
        
        return {
            "source_collections": source_collections,
            "target_collection": target_collection,
            "documents_merged": total_documents,
            "status": "success",
        }
    
    def list_collections(self) -> list[str]:
        """
        List all available collections.
        
        Returns:
            List of collection names
        """
        collections = self.db.list_collections()
        return [col.name for col in collections]
    
    def get_collection_stats(self, collection: str) -> dict[str, Any]:
        """
        Get statistics for a collection.
        
        Args:
            collection: Collection name
        
        Returns:
            Collection statistics
        """
        col = self.db.get_collection(collection)
        count = col.count()
        
        # Get sample documents to extract metadata
        sample = col.get(limit=1)
        metadata_keys = list(sample["metadatas"][0].keys()) if sample["metadatas"] else []
        
        return {
            "collection": collection,
            "document_count": count,
            "metadata_fields": metadata_keys,
        }
