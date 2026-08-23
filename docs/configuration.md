# CorpusRAG Configuration Guide

This guide covers all aspects of configuring CorpusRAG, from basic setup to advanced customization.

## Configuration System Overview

CorpusRAG uses a hierarchical YAML-based configuration system that allows flexible customization while maintaining sensible defaults. The configuration system supports:

- **Hierarchical loading**: Base configuration + tool-specific overrides
- **Environment variables**: Runtime overrides using the `CC_*` prefix
- **CLI arguments**: Highest precedence overrides
- **Deep merging**: Nested configuration sections merge intelligently
- **Type validation**: Configuration values are validated and type-checked

## Configuration Loading Order

Configuration values are loaded in the following order (later values override earlier ones):

1. **Base Configuration** (`configs/base.yaml`) - Shared defaults
2. **Tool-specific Configuration** (if applicable) - Tool overrides
3. **Environment Variables** (`CC_*` prefix) - Runtime overrides
4. **CLI Arguments** - Highest precedence

### Example Loading Process

```bash
# Base config has llm.model = "gemma4:26b-a4b-it-q4_K_M"
# Environment: CC_LLM_MODEL=mistral
# CLI: --model qwen3

# Final result: model = "qwen3" (CLI wins)
```

## Base Configuration

The base configuration file (`configs/base.yaml`) contains shared settings inherited by all tools. A fully commented reference lives in `configs/base.example.yaml`.

### Base Configuration Sections

```yaml
# CorpusRAG Base Configuration
# This file contains shared settings inherited by all tools

llm:
  backend: ollama                    # ollama | openai_compatible | anthropic_compatible
  endpoint: http://localhost:11434
  model: gemma4:26b-a4b-it-q4_K_M
  timeout_seconds: 120.0
  temperature: 0.7
  max_tokens: null                   # null for model default
  api_key: null                      # For cloud providers
  fallback_models: []                # Fallback model list

embedding:
  backend: ollama                    # ollama | sentence-transformers
  model: embeddinggemma
  dimensions: null                   # Auto-detect if null

database:
  backend: chromadb
  mode: persistent                   # persistent | http
  persist_directory: ./chroma_store  # For persistent mode
  host: localhost                    # For HTTP mode
  port: 8000                         # For HTTP mode

paths:
  vault: ./vault                     # Document storage
  scratch_dir: ./scratch             # Temporary files
  output_dir: ./output               # Generated content
```

## Collection names

Ingest, query, flashcards, summaries, and quizzes share one prefix. The
user-facing name `notes` is stored as `rag_notes`.

| Tool | Chroma name | Example flag |
|------|-------------|--------------|
| RAG ingest / query / TUI | `rag_<name>` | `--collection notes` |
| Flashcards / summaries / quizzes | `rag_<name>` | `-c notes` |

Do not create separate `flashcards_*` / `summaries_*` / `quizzes_*` stores.
Parent documents for retrieval live under `parent_store/<collection>/`.

Video OCR writes markdown files; the lecture pipeline indexes transcripts
through RAG ingest (still `rag_<course>_LectureNN`). The `video.collection_prefix`
setting is unused for Chroma.

## Configuration Sections

### LLM Configuration

Controls how CorpusRAG connects to Large Language Models.

```yaml
llm:
  backend: ollama                    # ollama | openai_compatible | anthropic_compatible
  endpoint: http://localhost:11434   # LLM service endpoint
  model: gemma4:26b-a4b-it-q4_K_M    # Primary model name
  timeout_seconds: 120.0             # Request timeout
  temperature: 0.7                   # Sampling temperature
  max_tokens: null                   # Max response tokens (null=model default)
  api_key: null                      # API key for cloud providers
  fallback_models:                   # Fallback models if primary fails
    - mistral:latest
    - neural-chat:latest
```

#### Supported Backends

The `backend` value must be one of: `ollama`, `openai_compatible`, or `anthropic_compatible`.

**Ollama Backend** (`backend: ollama`):
```yaml
llm:
  backend: ollama
  endpoint: http://localhost:11434
  model: gemma4:26b-a4b-it-q4_K_M
  # No API key required
```

**OpenAI Compatible** (`backend: openai_compatible`):
```yaml
llm:
  backend: openai_compatible
  endpoint: https://api.openai.com/v1
  model: gpt-4o
  api_key: sk-your-api-key-here
```

**Anthropic Compatible** (`backend: anthropic_compatible`):
```yaml
llm:
  backend: anthropic_compatible
  endpoint: https://api.anthropic.com
  model: claude-sonnet-4
  api_key: your-anthropic-api-key
```

### Embedding Configuration

Controls document embedding generation for vector search.

```yaml
embedding:
  backend: ollama                    # ollama | sentence-transformers
  model: embeddinggemma              # Embedding model name
  dimensions: null                   # Vector dimensions (auto-detect if null)
```

#### Ollama Embeddings

```yaml
embedding:
  backend: ollama
  model: embeddinggemma             # Or: nomic-embed-text, mxbai-embed-large
  dimensions: null                   # Auto-detected from model
```

#### Sentence-Transformers Embeddings

```yaml
embedding:
  backend: sentence-transformers
  model: all-MiniLM-L6-v2          # HuggingFace model name
  dimensions: 384                   # Model-specific dimensions
```

> **Note:** All embeddings in a collection must share the same dimensions. Changing this setting requires re-ingesting documents.

### Database Configuration

Controls the ChromaDB vector database connection.

```yaml
database:
  backend: chromadb
  mode: persistent                   # persistent | http
  persist_directory: ./chroma_store  # For persistent mode
  host: localhost                    # For HTTP mode
  port: 8000                         # For HTTP mode
```

#### Persistent Mode (Local Files)

```yaml
database:
  backend: chromadb
  mode: persistent
  persist_directory: ./chroma_store
```

Best for:
- Single-user setups
- Development
- Local testing
- Offline usage

#### HTTP Mode (Client-Server)

```yaml
database:
  backend: chromadb
  mode: http
  host: localhost                    # ChromaDB server host
  port: 8000                         # ChromaDB server port
```

Best for:
- Multi-user environments
- Docker deployments
- Shared databases
- Production setups

### Paths Configuration

Controls file system locations for various data.

```yaml
paths:
  vault: ./vault                     # Document storage directory
  scratch_dir: ./scratch             # Temporary files
  output_dir: ./output               # Generated content output
```

#### Custom Path Examples

```yaml
paths:
  vault: ~/Documents/corpus-vault
  scratch_dir: ~/.cache/corpusrag
  output_dir: ~/Documents/corpus-output
```

## Tool-Specific Configuration

Individual tools extend the base configuration with tool-specific settings.

### RAG Configuration

CorpusRAG uses a parent-child retrieval architecture: parent documents are split into smaller child chunks that are embedded and indexed for search.

```yaml
rag:
  chunking:
    child_chunk_size: 400            # Size of each child chunk in characters
    child_chunk_overlap: 50          # Overlap between consecutive child chunks
  retrieval:
    top_k_semantic: 25               # Child chunks from vector search before parent collapse
    top_k_bm25: 25                   # BM25 keyword hits before fusion
    top_k_final: 10                  # Final parent documents returned to the LLM
    rrf_k: 80                        # Reciprocal Rank Fusion parameter
  reranking:
    enabled: true
    model: cross-encoder/ms-marco-MiniLM-L-6-v2
  parent_store:
    path: ./parent_store             # Parents stored under parent_store/<collection>/
  collection_prefix: rag             # Collection name prefix (e.g. rag_notes)
```

### Video Configuration

Transcribe videos to text (via faster-whisper) and clean them with the LLM.

```yaml
video:
  whisper_model: medium.en           # tiny.en | base.en | small.en | medium.en | large-v2
  whisper_device: cpu                # cuda | cpu | mps
  whisper_compute_type: int8         # float32 | float16 | int8
  whisper_language: en               # ISO 639-1 code, or "auto" to auto-detect
  models_dir: ./models/whisper       # Cache directory for downloaded models
  clean_model: gemma4:26b-a4b-it-q4_K_M   # Model used for transcript cleaning
  output_format: markdown            # markdown | text | json
  include_timestamps: false          # Include timestamps in transcript output
  collection_prefix: videos          # Unused for Chroma; lecture pipeline uses rag_
  auto_ingest: true                  # Ingest transcripts into RAG after processing
  supported_extensions:              # Recognized video file extensions
    - .mp4
    - .mkv
    - .mov
    - .avi
    - .webm
    - .m4v
    - .zoom
```

### Summaries Configuration

```yaml
summaries:
  collection_prefix: rag             # Same store as RAG ingest (rag_<name>)
  summary_length: medium             # short | medium | long
  llm:
    model: gemma4:26b-a4b-it-q4_K_M
    temperature: 0.3
    max_tokens: 500
  prompt_template: |                 # Variables: {length}, {text}
    Generate a {length} summary of the following text:
    {text}
```

### Flashcards Configuration

```yaml
flashcards:
  collection_prefix: rag             # Same store as RAG ingest (rag_<name>)
  difficulty: intermediate           # beginner | intermediate | advanced
  count: 15                          # Number of flashcards to generate
  llm:
    model: gemma4:26b-a4b-it-q4_K_M
    temperature: 0.5
  format: markdown                   # markdown | json | csv
  prompt_template: |                 # Variables: {count}, {difficulty}, {text}
    Generate {count} flashcards at {difficulty} difficulty level from the following text:
    {text}
```

### Quizzes Configuration

```yaml
quizzes:
  collection_prefix: rag             # Same store as RAG ingest (rag_<name>)
  count: 10                          # Number of questions to generate
  format: markdown                   # markdown | json | csv
  difficulty: intermediate           # beginner | intermediate | advanced
  llm:
    model: gemma4:26b-a4b-it-q4_K_M
    temperature: 0.4
  question_types:                    # Available question types
    - multiple_choice
    - true_false
    - short_answer
  prompt_template: |                 # Variables: {count}, {difficulty}, {question_types}, {text}
    Generate a quiz with {count} questions at {difficulty} difficulty level.
    Include a mix of question types: {question_types}.
    {text}
```

## Environment Variable Overrides

Any configuration value can be overridden using environment variables with the `CC_` prefix.

### Environment Variable Format

Convert YAML paths to environment variables:
- Nested keys: `llm.model` → `CC_LLM_MODEL`
- Deeper nesting: `rag.chunking.child_chunk_size` → `CC_RAG_CHUNKING_CHILD_CHUNK_SIZE`
- Array indices: Not directly supported

### Common Environment Variables

```bash
# LLM Configuration
export CC_LLM_ENDPOINT=http://localhost:11434
export CC_LLM_MODEL=mistral
export CC_LLM_BACKEND=ollama
export CC_LLM_TEMPERATURE=0.7
export CC_LLM_API_KEY=your-api-key

# Database Configuration
export CC_DATABASE_MODE=http
export CC_DATABASE_HOST=chromadb
export CC_DATABASE_PORT=8000

# Paths Configuration
export CC_PATHS_VAULT=/path/to/documents
export CC_PATHS_OUTPUT_DIR=/path/to/output

# Tool-specific Configuration
export CC_RAG_CHUNKING_CHILD_CHUNK_SIZE=800
export CC_FLASHCARDS_COUNT=20
```

### Docker Environment Variables

For Docker deployments, you can set environment variables in your compose file:

```yaml
services:
  corpus-mcp:
    image: corpusrag:latest
    environment:
      - CC_DATABASE_MODE=http
      - CC_DATABASE_HOST=chromadb
      - CC_DATABASE_PORT=8000
      - CC_LLM_ENDPOINT=http://ollama:11434
      - CC_LLM_MODEL=gemma4:26b-a4b-it-q4_K_M
```

## Configuration Examples

### Example 1: Minimal Local Setup

```yaml
# configs/minimal.yaml
llm:
  endpoint: http://localhost:11434
  model: gemma4:26b-a4b-it-q4_K_M

database:
  mode: persistent
  persist_directory: ./chroma_store
```

### Example 2: Production Docker Setup

```yaml
# configs/production.yaml
llm:
  endpoint: http://ollama:11434
  model: gemma4:26b-a4b-it-q4_K_M
  timeout_seconds: 180.0

database:
  mode: http
  host: chromadb
  port: 8000

paths:
  vault: /app/data/vault
  scratch_dir: /tmp/corpus-scratch
  output_dir: /app/data/output
```

### Example 3: Cloud LLM Setup

```yaml
# configs/cloud.yaml
llm:
  backend: openai_compatible
  endpoint: https://api.openai.com/v1
  model: gpt-4o
  api_key: null              # Set via CC_LLM_API_KEY environment variable
  temperature: 0.3
  max_tokens: 4000

embedding:
  backend: sentence-transformers
  model: all-MiniLM-L6-v2
  dimensions: 384

database:
  mode: http
  host: your-chromadb-server.com
  port: 8000
```

### Example 4: Advanced RAG Configuration

```yaml
# configs/advanced-rag.yaml
llm:
  endpoint: http://localhost:11434
  model: gemma4:26b-a4b-it-q4_K_M
  fallback_models:
    - mistral:latest
    - neural-chat:latest

embedding:
  backend: ollama
  model: embeddinggemma

database:
  mode: persistent
  persist_directory: ./advanced_chroma

rag:
  chunking:
    child_chunk_size: 800
    child_chunk_overlap: 100
  retrieval:
    top_k_semantic: 50
    top_k_bm25: 25
    top_k_final: 10
    rrf_k: 80

paths:
  vault: ~/Documents/research-papers
  output_dir: ~/Documents/rag-outputs
```

## Configuration Validation

CorpusRAG validates configuration at startup and provides clear error messages for invalid settings.

### Common Validation Errors

**Invalid Backend**:
```
Error: Invalid LLM backend 'invalid_backend'. Must be one of: ollama, openai_compatible, anthropic_compatible
```

**Type Mismatch**:
```
Error: Field 'llm.temperature' must be a float, got string
```

## Configuration Best Practices

### 1. Use Base Configuration

Always start with a base configuration and override only what you need:

```yaml
# Good: Minimal overrides
llm:
  model: mistral:latest  # Only override what's different

# Avoid: Repeating the entire configuration
```

### 2. Environment-Specific Configs

Use separate configuration files for different environments:

```
configs/
├── base.yaml        # Shared defaults
├── development.yaml # Local development
├── production.yaml  # Production deployment
└── testing.yaml     # Test environment
```

### 3. Secure API Keys

Never commit API keys to version control. Use environment variables:

```yaml
llm:
  api_key: null  # Set via CC_LLM_API_KEY environment variable
```

### 4. Use Absolute Paths in Production

For production deployments, use absolute paths:

```yaml
paths:
  vault: /app/data/vault
  output_dir: /app/data/output

database:
  persist_directory: /app/data/chroma
```

### 5. Resource Limits

Consider resource limits for production:

```yaml
llm:
  timeout_seconds: 300.0  # Longer timeout for production
  max_tokens: 4000        # Reasonable limit

rag:
  chunking:
    child_chunk_size: 800   # Larger chunks for better context
  retrieval:
    top_k_final: 10         # More results for better recall
```

## Troubleshooting Configuration

### Common Issues

**Database Connection Failed**:
- Check `database.mode` and connection details
- Verify ChromaDB server is running (for HTTP mode)
- Check file permissions (for persistent mode)

**LLM Connection Failed**:
- Verify `llm.endpoint` is correct and accessible
- Check if `api_key` is set (for cloud providers)
- Confirm the model is available

**Path Issues**:
- Ensure directories exist and are writable
- Use absolute paths for production
- Check file permissions

**Environment Variable Not Applied**:
- Verify variable name format (`CC_SECTION_FIELD`)
- Check the variable is exported in your shell
- Confirm no typos in variable names

## Command-Line Entry Points

CorpusRAG installs two entry points:

- `corpus` - the main CLI for ingestion, querying, generation, and orchestration
- `corpus-mcp-server` - the MCP server for tool integrations

You can pass a config file to the main CLI with the `--config` flag:

```bash
corpus --config my-config.yaml rag ingest ./vault --collection notes
```

## Advanced Configuration

### Custom Configuration Classes

For advanced use cases, you can extend the configuration system by subclassing `BaseConfig`:

```python
from config.base import BaseConfig
from dataclasses import dataclass, field

@dataclass
class MyCustomConfig(BaseConfig):
    """Custom configuration for a specialized tool."""

    custom_setting: str = "default_value"
    advanced_options: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "MyCustomConfig":
        # Custom loading logic
        base_config = super().from_dict(data)
        return cls(
            llm=base_config.llm,
            embedding=base_config.embedding,
            database=base_config.database,
            paths=base_config.paths,
            custom_setting=data.get("custom_setting", "default_value"),
        )
```

### Configuration Hooks

You can add configuration validation hooks:

```python
def validate_config(config: BaseConfig) -> None:
    """Custom configuration validation."""
    if config.llm.temperature > 2.0:
        raise ValueError("Temperature must be <= 2.0")

    if not config.paths.vault.exists():
        config.paths.vault.mkdir(parents=True, exist_ok=True)
```

This configuration system provides flexible, powerful configuration management while maintaining simplicity for common use cases.
