"""RAG agent orchestration."""

from typing import Any

from db import DatabaseBackend
from llm import PromptTemplates, create_backend

from .config import RAGConfig
from .retriever import RAGRetriever, RetrievedDocument
from .session import SessionManager


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
        self.session_manager = SessionManager()
        # Create LLM backend for generation
        self.llm_backend = create_backend(config.llm.to_backend_config())

    def _filter_context(self, history: list[dict]) -> list[dict]:
        """Filter out excluded messages from context.

        Args:
            history: Conversation history

        Returns:
            Filtered history with only included messages
        """
        return [msg for msg in history if msg.get("included", True)]

    def query(
        self,
        query: str,
        collection: str,
        top_k: int | None = None,
        stream: bool = False,
        conversation_history: list[dict[str, str]] | None = None,
        where: dict[str, Any] | None = None,
    ) -> str:
        """Execute RAG query with optional metadata filtering.

        Args:
            query: User query
            collection: Collection name to search
            top_k: Number of documents to retrieve
            stream: Whether to stream the response (not yet implemented)
            conversation_history: Previous conversation messages
            where: Metadata filter dict for tags, sections, etc.

        Returns:
            Response text
        """
        import time

        from utils.benchmarking import benchmarker

        start_total = time.perf_counter()
        try:
            # 1. Retrieve
            start_retrieval = time.perf_counter()
            # Retrieve relevant parent documents
            documents = self.retriever.retrieve(query, collection, top_k, where=where)
            retrieval_time = time.perf_counter() - start_retrieval

            # Convert documents to format expected by prompt template
            context_chunks = []
            for doc in documents:
                context_chunks.append(
                    {
                        "text": doc.text,
                        "source": doc.metadata.get("source_file", "unknown"),
                        "score": doc.score,
                    }
                )

            # Filter conversation history to include only selected messages
            filtered_history = None
            if conversation_history:
                filtered_history = self._filter_context(conversation_history)
                # Truncate to fit context window
                # Keeping last 10 messages (5 exchanges) as a default window
                filtered_history = filtered_history[-10:]

            # Build prompt with context using the prompt template
            prompt = PromptTemplates.rag_response(
                query=query,
                context_chunks=context_chunks,
                conversation_history=filtered_history,
            )

            # 2. Generate
            start_gen = time.perf_counter()
            # Generate response using LLM
            if stream:
                # TODO: Implement streaming response
                response = self.llm_backend.complete(prompt)
                result_text = response.text
            else:
                response = self.llm_backend.complete(prompt)
                result_text = response.text
            gen_time = time.perf_counter() - start_gen

            total_time = time.perf_counter() - start_total
            benchmarker.record(retrieval_time, gen_time, total_time)

            return result_text

        except Exception as e:
            return f"Error generating response: {e}"

    def chat(
        self,
        message: str,
        collection: str,
        session_id: str | None = None,
        stream: bool = False,
        where: dict[str, Any] | None = None,
    ) -> str:
        """Chat with RAG agent maintaining conversation history.

        Args:
            message: User message
            collection: Collection name to search
            session_id: Optional session ID for conversation history
            stream: Whether to stream the response
            where: Metadata filter dict for tags, sections, etc.

        Returns:
            Response text
        """
        # Load existing history if session_id is provided
        history = []
        if session_id:
            history = self.session_manager.load_session(session_id)

        # Execute query with history
        response = self.query(
            message,
            collection,
            stream=stream,
            conversation_history=history,
            where=where,
        )

        # Update and save history with inclusion state
        if session_id:
            history.append({"role": "user", "content": message, "included": True})
            history.append({"role": "assistant", "content": response, "included": True})
            self.session_manager.save_session(session_id, history)

        return response

    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedDocument]:
        """Retrieve relevant parent documents without generating a response.

        Args:
            query: Search query
            collection: Collection name to search
            top_k: Number of documents to retrieve
            where: Metadata filter dict for tags, sections, etc.

        Returns:
            List of retrieved parent documents
        """
        return self.retriever.retrieve(query, collection, top_k, where=where)
