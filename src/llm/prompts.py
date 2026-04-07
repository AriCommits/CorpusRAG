"""
Prompt templates and utilities for LLM generation.

Provides standardized prompts for various content generation tasks.
"""

from typing import Any


class PromptTemplates:
    """Collection of prompt templates for different content types."""

    @staticmethod
    def flashcard_generation(
        documents: list[str],
        difficulty: str = "intermediate",
        count: int = 15,
        topic: str | None = None,
    ) -> str:
        """Generate prompt for flashcard creation.
        
        Args:
            documents: List of document texts
            difficulty: Difficulty level (beginner, intermediate, advanced)
            count: Number of flashcards to generate
            topic: Optional specific topic to focus on
            
        Returns:
            Formatted prompt for flashcard generation
        """
        topic_instruction = f" about {topic}" if topic else ""
        
        return f"""Create {count} flashcards{topic_instruction} based on the provided documents. 

DIFFICULTY LEVEL: {difficulty.title()}

DOCUMENTS:
{'='*50}
{chr(10).join(f"Document {i+1}:{chr(10)}{doc}{chr(10)}" for i, doc in enumerate(documents))}
{'='*50}

REQUIREMENTS:
- Generate exactly {count} flashcards
- Difficulty level: {difficulty}
- Each flashcard should have a clear, specific question and a complete answer
- Focus on key concepts, definitions, facts, and relationships
- Vary question types (what, how, why, when, who, etc.)
- Ensure answers are accurate and based on the provided documents
- Make questions challenging but fair for {difficulty} level

FORMAT:
For each flashcard, provide:
Q: [Clear, specific question]
A: [Complete, accurate answer]

---

Begin generating flashcards:"""

    @staticmethod
    def summary_generation(
        documents: list[str],
        length: str = "medium",
        topic: str | None = None,
    ) -> str:
        """Generate prompt for summary creation.
        
        Args:
            documents: List of document texts
            length: Summary length (short, medium, long)
            topic: Optional specific topic to focus on
            
        Returns:
            Formatted prompt for summary generation
        """
        length_guidance = {
            "short": "1-2 paragraphs, focusing on the most essential points",
            "medium": "3-5 paragraphs, covering main topics and key details", 
            "long": "6+ paragraphs, providing comprehensive coverage with examples",
        }
        
        topic_instruction = f" focusing specifically on {topic}" if topic else ""
        
        return f"""Create a {length} summary of the provided documents{topic_instruction}.

DOCUMENTS:
{'='*50}
{chr(10).join(f"Document {i+1}:{chr(10)}{doc}{chr(10)}" for i, doc in enumerate(documents))}
{'='*50}

REQUIREMENTS:
- Length: {length_guidance.get(length, length)}
- Structure: Clear introduction, body, and conclusion
- Style: Professional, clear, and accessible
- Content: Focus on main ideas, key concepts, and important details
- Accuracy: Base summary entirely on provided documents
- Coherence: Ensure logical flow between ideas

Begin the summary:"""

    @staticmethod
    def quiz_generation(
        documents: list[str],
        difficulty: str = "intermediate",
        count: int = 10,
        topic: str | None = None,
    ) -> str:
        """Generate prompt for quiz creation.
        
        Args:
            documents: List of document texts
            difficulty: Difficulty level (beginner, intermediate, advanced)
            count: Number of quiz questions to generate
            topic: Optional specific topic to focus on
            
        Returns:
            Formatted prompt for quiz generation
        """
        topic_instruction = f" about {topic}" if topic else ""
        
        return f"""Create a {count}-question quiz{topic_instruction} based on the provided documents.

DIFFICULTY LEVEL: {difficulty.title()}

DOCUMENTS:
{'='*50}
{chr(10).join(f"Document {i+1}:{chr(10)}{doc}{chr(10)}" for i, doc in enumerate(documents))}
{'='*50}

REQUIREMENTS:
- Generate exactly {count} questions
- Difficulty level: {difficulty}
- Mix of question types: multiple choice, true/false, short answer
- Cover different aspects of the material
- Include clear, unambiguous correct answers
- For multiple choice: provide 4 options (A, B, C, D) with one correct answer
- Base all questions and answers on the provided documents

FORMAT:
Question 1: [Question text]
Type: [Multiple Choice/True-False/Short Answer]
A) [Option A] (for multiple choice only)
B) [Option B] (for multiple choice only) 
C) [Option C] (for multiple choice only)
D) [Option D] (for multiple choice only)
Correct Answer: [A/B/C/D/True/False or short answer text]
Explanation: [Brief explanation of why this is correct]

---

Begin generating quiz questions:"""

    @staticmethod
    def rag_response(
        query: str,
        context_chunks: list[dict[str, Any]],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate prompt for RAG response generation.
        
        Args:
            query: User's question or query
            context_chunks: List of relevant document chunks with metadata
            conversation_history: Previous conversation messages
            
        Returns:
            Formatted prompt for RAG response generation
        """
        # Format context chunks
        context_text = ""
        for i, chunk in enumerate(context_chunks, 1):
            source = chunk.get("source", "Unknown")
            text = chunk.get("text", "")
            score = chunk.get("score", 0.0)
            
            context_text += f"Context {i} (Source: {source}, Relevance: {score:.3f}):\n{text}\n\n"
        
        # Format conversation history if provided
        history_text = ""
        if conversation_history:
            history_text = "CONVERSATION HISTORY:\n"
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_text += f"{role.title()}: {content}\n"
            history_text += "\n"
        
        return f"""{history_text}RELEVANT CONTEXT:
{'='*50}
{context_text}
{'='*50}

USER QUERY: {query}

INSTRUCTIONS:
- Answer the user's query using the provided context
- If the context doesn't contain enough information, say so clearly
- Cite specific sources when making claims
- Be accurate, helpful, and concise
- If this is part of an ongoing conversation, acknowledge previous context
- If the query is unclear, ask for clarification

RESPONSE:"""