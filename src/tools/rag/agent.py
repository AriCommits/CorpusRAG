"""RAG agent orchestration."""

from typing import Any, Iterator, Optional

from corpus_callosum.db import DatabaseBackend
from corpus_callosum.llm import create_backend, PromptTemplates

from .config import RAGConfig
from .retriever import RAGRetriever, RetrievedChunk


class RAGAgent:
    """RAG agent for retrieval-augmented generation."""

    def __init__(self, config: RAGConfig, db: DatabaseBackend):
        """Initialize RAG agent.

        Args:
            config: RAG configuration
            db: Database backend
        """
        self.config = config
        self.db = db
        self.retriever = RAGRetriever(config, db)
        # Create LLM backend for generation
        self.llm_backend = create_backend(config.llm.to_backend_config())

    def query(
        self,
        query: str,
        collection: str,
        top_k: Optional[int] = None,
        stream: bool = False,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """Execute RAG query.

        Args:
            query: User query
            collection: Collection name to search
            top_k: Number of documents to retrieve
            stream: Whether to stream the response (not yet implemented)
            conversation_history: Previous conversation messages

        Returns:
            Response text
        """
        try:
            # Retrieve relevant chunks
            chunks = self.retriever.retrieve(query, collection, top_k)

            # Convert chunks to format expected by prompt template
            context_chunks = []
            for chunk in chunks:
                context_chunks.append({
                    "text": chunk.text,
                    "source": chunk.metadata.get("source_file", "unknown"),
                    "score": chunk.score,
                })

            # Build prompt with context using the prompt template
            prompt = PromptTemplates.rag_response(
                query=query,
                context_chunks=context_chunks,
                conversation_history=conversation_history,
            )

            # Generate response using LLM
            if stream:
                # TODO: Implement streaming response
                response = self.llm_backend.complete(prompt)
                return response.text
            else:
                response = self.llm_backend.complete(prompt)
                return response.text

        except Exception as e:
            return f"Error generating response: {e}"

    def chat(
        self,
        message: str,
        collection: str,
        session_id: Optional[str] = None,
        stream: bool = False,
    ) -> str:
        """Chat with RAG agent maintaining conversation history.

        Args:
            message: User message
            collection: Collection name to search
            session_id: Optional session ID for conversation history
            stream: Whether to stream the response

        Returns:
            Response text
        """
        # TODO: Implement proper conversation history storage
        # For now, just use single query
        conversation_history = None
        
        if session_id:
            # Placeholder for loading conversation history
            # In full implementation, this would load from storage
            conversation_history = []
        
        response = self.query(
            message, 
            collection, 
            stream=stream, 
            conversation_history=conversation_history
        )
        
        if session_id:
            # Placeholder for saving conversation history
            # In full implementation, this would save to storage
            pass
        
        return response

    def retrieve(self, query: str, collection: str, top_k: Optional[int] = None) -> list[RetrievedChunk]:
        """Retrieve relevant chunks without generating a response.

        Args:
            query: Search query
            collection: Collection name to search
            top_k: Number of documents to retrieve

        Returns:
            List of retrieved chunks
        """
        return self.retriever.retrieve(query, collection, top_k)
