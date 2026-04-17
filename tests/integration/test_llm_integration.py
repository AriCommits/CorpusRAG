"""
Test script for LLM integration in CorpusCallosum.

Simple test to verify the LLM backend works correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm import LLMBackendType, LLMConfig, PromptTemplates, create_backend


def test_ollama_backend():
    """Test Ollama backend connection and generation."""
    print("Testing Ollama backend...")

    config = LLMConfig(
        backend=LLMBackendType.OLLAMA,
        endpoint="http://localhost:11434",
        model="llama3.2",  # Fallback to available model
    )

    try:
        backend = create_backend(config)
        print("✓ Backend created successfully")

        # Test simple completion
        response = backend.complete("What is the capital of France?")
        print(f"✓ Simple completion works. Response: {response.text[:100]}...")

        # Test flashcard generation
        documents = [
            "Paris is the capital and largest city of France. It is located on the Seine River.",
            "The Eiffel Tower is a famous landmark in Paris, built in 1889 for the World's Fair.",
        ]

        flashcard_prompt = PromptTemplates.flashcard_generation(
            documents=documents, difficulty="beginner", count=2, topic="Paris"
        )

        flashcard_response = backend.complete(flashcard_prompt)
        print(
            f"✓ Flashcard generation works. Response: {flashcard_response.text[:200]}..."
        )

        return True

    except Exception as e:
        print(f"✗ Error testing Ollama backend: {e}")
        return False


def test_prompt_templates():
    """Test prompt template generation."""
    print("\nTesting prompt templates...")

    try:
        # Test flashcard prompt
        PromptTemplates.flashcard_generation(
            documents=["Test document content"],
            difficulty="intermediate",
            count=3,
        )
        print("✓ Flashcard prompt template works")

        # Test summary prompt
        PromptTemplates.summary_generation(
            documents=["Test document content"],
            length="medium",
        )
        print("✓ Summary prompt template works")

        # Test quiz prompt
        PromptTemplates.quiz_generation(
            documents=["Test document content"],
            difficulty="intermediate",
            count=3,
        )
        print("✓ Quiz prompt template works")

        # Test RAG prompt
        PromptTemplates.rag_response(
            query="What is this about?",
            context_chunks=[
                {"text": "Test content", "source": "test.txt", "score": 0.9}
            ],
        )
        print("✓ RAG prompt template works")

        return True

    except Exception as e:
        print(f"✗ Error testing prompt templates: {e}")
        return False


def main():
    """Run all tests."""
    print("CorpusCallosum LLM Integration Test")
    print("=" * 40)

    # Test prompt templates (no network needed)
    templates_ok = test_prompt_templates()

    # Test Ollama backend (needs Ollama running)
    print("\nNote: Ollama backend test requires Ollama to be running locally")
    print("If you don't have Ollama installed, this test will fail")
    ollama_ok = test_ollama_backend()

    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Prompt Templates: {'✓ PASS' if templates_ok else '✗ FAIL'}")
    print(f"Ollama Backend: {'✓ PASS' if ollama_ok else '✗ FAIL'}")

    if templates_ok and ollama_ok:
        print("\n🎉 All tests passed! LLM integration is working correctly.")
        return 0
    elif templates_ok:
        print("\n⚠️  Prompt templates work, but Ollama connection failed.")
        print("Make sure Ollama is running: ollama serve")
        return 1
    else:
        print("\n❌ Tests failed. Check the error messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
