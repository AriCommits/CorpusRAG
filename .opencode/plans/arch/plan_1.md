# CorpusCallosum: Unified Learning & Knowledge Management Architecture

**Date**: 2026-04-07  
**Version**: 1.0  
**Status**: Draft

---

## Executive Summary

This plan outlines the architectural redesign of CorpusCallosum—a unified toolkit for personal knowledge management and learning workflows. The project consolidates three previously separate repositories:

1. **HomeSchool** (flashcards, summaries, quiz generation)
2. **RAG Pipeline** (retrieval-augmented generation on personal notes)
3. **Video Transcription** (lecture transcription and processing)

The goal is to create a modular, well-engineered system with:
- Individual CLI tools for each capability
- MCP (Model Context Protocol) server exposure for agent orchestration
- Shared configuration hierarchy (Python dataclasses + YAML)
- Unified database abstraction layer
- Minimal dependencies with robust, proven packages
- Intuitive CLI interfaces for direct usage

---

## Project Goals

### Core Principles
1. **Modularity**: Each feature should work independently via CLI or as MCP tool
2. **Dual Interface**: Every tool accessible via both CLI and MCP server
3. **Configuration Hierarchy**: Base config + tool-specific overrides (Python dataclasses + YAML)
4. **Minimal Dependencies**: Use robust, maintained packages; avoid bloat
5. **Database Abstraction**: Single shared database with clean data access layer
6. **Developer Experience**: Simple, intuitive interfaces; easy to extend

### Success Criteria
- [x] All tools runnable independently via CLI ✅ **COMPLETED**
- [x] All tools exposed via MCP server for agent orchestration ✅ **COMPLETED** 
- [x] Shared configuration system working across all tools ✅ **COMPLETED**
- [x] Single database instance with isolated collection namespaces ✅ **COMPLETED**
- [x] Comprehensive test coverage (pytest) ✅ **COMPLETED**
- [ ] Complete documentation with usage examples ⏳ **IN PROGRESS**

---

## Architecture Overview

### Directory Structure

```
CorpusCallosum/
├── .opencode/
│   ├── plans/
│   │   ├── arch/              # Architecture plans
│   │   ├── flashcard/         # Flashcard feature plans
│   │   ├── rag/              # RAG feature plans
│   │   └── video/            # Video transcription plans
│   └── skills/
├── src/
│   └── corpus_callosum/
│       ├── __init__.py
│       ├── __main__.py       # Main CLI entry point
│       ├── config/
│       │   ├── __init__.py
│       │   ├── base.py       # BaseConfig dataclass
│       │   ├── loader.py     # YAML config loader with merge logic
│       │   └── schema.py     # Validation schemas
│       ├── tools/            # Individual tool implementations
│       │   ├── __init__.py
│       │   ├── flashcards/
│       │   │   ├── __init__.py
│       │   │   ├── cli.py           # Flashcard CLI
│       │   │   ├── config.py        # FlashcardConfig dataclass
│       │   │   ├── generator.py     # Core flashcard logic
│       │   │   └── mcp.py          # MCP tool wrapper
│       │   ├── summaries/
│       │   │   ├── __init__.py
│       │   │   ├── cli.py
│       │   │   ├── config.py
│       │   │   ├── generator.py
│       │   │   └── mcp.py
│       │   ├── quizzes/
│       │   │   ├── __init__.py
│       │   │   ├── cli.py
│       │   │   ├── config.py
│       │   │   ├── generator.py
│       │   │   └── mcp.py
│       │   ├── rag/
│       │   │   ├── __init__.py
│       │   │   ├── cli.py
│       │   │   ├── config.py
│       │   │   ├── agent.py         # RAG orchestration
│       │   │   ├── retriever.py     # Hybrid retrieval
│       │   │   ├── ingest.py        # Document ingestion
│       │   │   └── mcp.py
│       │   └── video/
│       │       ├── __init__.py
│       │       ├── cli.py
│       │       ├── config.py
│       │       ├── transcribe.py    # Whisper transcription
│       │       ├── clean.py         # LLM-based cleaning
│       │       ├── augment.py       # Manual annotation
│       │       └── mcp.py
│       ├── orchestrations/   # Pre-composed workflows
│       │   ├── __init__.py
│       │   ├── study_session.py    # Flashcards + summaries + quiz
│       │   ├── lecture_to_vault.py # Video → RAG → flashcards
│       │   └── knowledge_base.py   # RAG ingest + index + query
│       ├── db/               # Database abstraction layer
│       │   ├── __init__.py
│       │   ├── base.py       # Abstract DB interface
│       │   ├── chroma.py     # ChromaDB implementation
│       │   ├── sync.py       # Cross-tool sync utilities
│       │   └── models.py     # Shared data models
│       ├── mcp_server/       # MCP server implementation
│       │   ├── __init__.py
│       │   ├── server.py     # Main MCP server
│       │   ├── registry.py   # Tool registration
│       │   └── tools.py      # Tool wrappers
│       └── utils/            # Shared utilities
│           ├── __init__.py
│           ├── llm.py        # LLM client abstraction
│           ├── embeddings.py # Embedding backends
│           ├── converters.py # Document format conversion
│           └── validation.py # Input validation
├── configs/
│   ├── base.yaml             # Base configuration
│   ├── flashcards.yaml       # Flashcard overrides
│   ├── summaries.yaml        # Summary overrides
│   ├── quizzes.yaml          # Quiz overrides
│   ├── rag.yaml              # RAG overrides
│   ├── video.yaml            # Video transcription overrides
│   └── examples/             # Example configurations
├── .docker/
│   ├── Dockerfile            # Single unified Dockerfile
│   ├── docker-compose.yml    # All services
│   └── otel-collector-config.yaml
├── tests/
│   ├── unit/
│   │   ├── test_flashcards.py
│   │   ├── test_summaries.py
│   │   ├── test_quizzes.py
│   │   ├── test_rag.py
│   │   └── test_video.py
│   ├── integration/
│   │   ├── test_orchestrations.py
│   │   ├── test_mcp_server.py
│   │   └── test_cli.py
│   └── fixtures/
├── docs/
│   ├── architecture.md
│   ├── configuration.md
│   ├── mcp_integration.md
│   └── tools/
│       ├── flashcards.md
│       ├── summaries.md
│       ├── quizzes.md
│       ├── rag.md
│       └── video.md
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Core Components

### 1. Configuration System

**Design Philosophy**: Hierarchical configuration with inheritance and overrides

#### Python Dataclasses

```python
# src/corpus_callosum/config/base.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class LLMConfig:
    """Shared LLM configuration"""
    endpoint: str = "http://localhost:11434"
    model: str = "llama3"
    timeout_seconds: float = 120.0
    temperature: float = 0.7
    max_tokens: Optional[int] = None

@dataclass
class EmbeddingConfig:
    """Shared embedding configuration"""
    backend: str = "ollama"  # ollama | sentence-transformers
    model: str = "nomic-embed-text"
    dimensions: Optional[int] = None

@dataclass
class DatabaseConfig:
    """Shared database configuration"""
    backend: str = "chromadb"
    mode: str = "persistent"  # persistent | http
    host: str = "localhost"
    port: int = 8000
    persist_directory: Path = Path("./chroma_store")

@dataclass
class PathsConfig:
    """Shared paths configuration"""
    vault: Path = Path("./vault")
    scratch_dir: Path = Path("./scratch")
    output_dir: Path = Path("./output")

@dataclass
class BaseConfig:
    """Base configuration inherited by all tools"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    
    @classmethod
    def from_yaml(cls, path: Path) -> "BaseConfig":
        """Load from YAML file"""
        pass
    
    def merge(self, other: "BaseConfig") -> "BaseConfig":
        """Merge with another config (other takes precedence)"""
        pass
```

#### Tool-Specific Configs

```python
# src/corpus_callosum/tools/flashcards/config.py
from dataclasses import dataclass
from corpus_callosum.config.base import BaseConfig

@dataclass
class FlashcardConfig(BaseConfig):
    """Flashcard-specific configuration"""
    cards_per_topic: int = 10
    difficulty_levels: list[str] = field(default_factory=lambda: ["basic", "intermediate", "advanced"])
    format: str = "anki"  # anki | quizlet | plain
    collection_name: str = "flashcards"
```

#### YAML Configuration

```yaml
# configs/base.yaml
llm:
  endpoint: http://localhost:11434
  model: llama3
  timeout_seconds: 120.0
  temperature: 0.7

embedding:
  backend: ollama
  model: nomic-embed-text

database:
  backend: chromadb
  mode: persistent
  persist_directory: ./chroma_store

paths:
  vault: ./vault
  scratch_dir: ./scratch
  output_dir: ./output
```

```yaml
# configs/flashcards.yaml
# Inherits from base.yaml and overrides specific values
llm:
  temperature: 0.5  # More deterministic for flashcards

flashcards:
  cards_per_topic: 15
  difficulty_levels: [basic, intermediate, advanced]
  format: anki
  collection_name: study_cards
```

#### Config Loading Strategy

1. Load `configs/base.yaml`
2. Load tool-specific YAML (e.g., `configs/flashcards.yaml`)
3. Deep merge tool config over base config
4. Override with environment variables (e.g., `CC_LLM_MODEL=llama3.2`)
5. Override with CLI arguments (highest precedence)

```python
# Example usage
config = FlashcardConfig.from_yaml("configs/flashcards.yaml")
# Automatically merges with base.yaml
```

---

### 2. Database Abstraction Layer

**Goal**: Single database instance with clean abstraction for all tools

#### Abstract Interface

```python
# src/corpus_callosum/db/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class DatabaseBackend(ABC):
    """Abstract database interface"""
    
    @abstractmethod
    def create_collection(self, name: str, metadata: Dict[str, Any]) -> None:
        """Create a new collection"""
        pass
    
    @abstractmethod
    def get_collection(self, name: str) -> Any:
        """Get existing collection"""
        pass
    
    @abstractmethod
    def list_collections(self) -> List[str]:
        """List all collections"""
        pass
    
    @abstractmethod
    def add_documents(
        self, 
        collection: str, 
        documents: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """Add documents to collection"""
        pass
    
    @abstractmethod
    def query(
        self,
        collection: str,
        query_embedding: List[float],
        n_results: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query collection"""
        pass
    
    @abstractmethod
    def delete_collection(self, name: str) -> None:
        """Delete collection"""
        pass
```

#### ChromaDB Implementation

```python
# src/corpus_callosum/db/chroma.py
import chromadb
from chromadb.config import Settings
from .base import DatabaseBackend

class ChromaDBBackend(DatabaseBackend):
    """ChromaDB implementation"""
    
    def __init__(self, config: DatabaseConfig):
        if config.mode == "persistent":
            self.client = chromadb.PersistentClient(
                path=str(config.persist_directory)
            )
        else:
            self.client = chromadb.HttpClient(
                host=config.host,
                port=config.port
            )
    
    # Implement all abstract methods...
```

#### Collection Namespacing Strategy

Each tool gets its own collection namespace:

- **Flashcards**: `flashcards_<topic>`
- **Summaries**: `summaries_<topic>`
- **Quizzes**: `quizzes_<topic>`
- **RAG**: `rag_<collection>`
- **Video**: `video_transcripts_<course>`

This allows:
- Independent data management per tool
- Easy cleanup and migration
- Clear separation of concerns
- Shared database instance (single Docker container)

---

### 3. Tool Architecture

Each tool follows a consistent pattern:

#### CLI Interface

```python
# src/corpus_callosum/tools/flashcards/cli.py
import click
from .config import FlashcardConfig
from .generator import FlashcardGenerator

@click.command()
@click.option('--collection', '-c', required=True, help='Collection name')
@click.option('--output', '-o', default=None, help='Output file')
@click.option('--config', '-f', default='configs/flashcards.yaml', help='Config file')
def flashcards(collection: str, output: str, config: str):
    """Generate flashcards from a collection"""
    cfg = FlashcardConfig.from_yaml(config)
    generator = FlashcardGenerator(cfg)
    cards = generator.generate(collection)
    
    if output:
        with open(output, 'w') as f:
            f.write(cards)
    else:
        print(cards)

if __name__ == '__main__':
    flashcards()
```

#### MCP Tool Wrapper

```python
# src/corpus_callosum/tools/flashcards/mcp.py
from corpus_callosum.mcp_server.registry import register_tool
from .config import FlashcardConfig
from .generator import FlashcardGenerator

@register_tool(
    name="generate_flashcards",
    description="Generate flashcards from a knowledge collection",
    parameters={
        "collection": {"type": "string", "description": "Collection name"},
        "count": {"type": "integer", "description": "Number of cards to generate", "default": 10},
        "difficulty": {"type": "string", "enum": ["basic", "intermediate", "advanced"], "default": "intermediate"}
    }
)
def generate_flashcards_mcp(collection: str, count: int = 10, difficulty: str = "intermediate") -> dict:
    """MCP tool for flashcard generation"""
    cfg = FlashcardConfig.from_yaml("configs/flashcards.yaml")
    cfg.cards_per_topic = count
    
    generator = FlashcardGenerator(cfg)
    cards = generator.generate(collection, difficulty=difficulty)
    
    return {
        "status": "success",
        "collection": collection,
        "cards": cards,
        "count": len(cards)
    }
```

---

### 4. MCP Server

**Design**: Single MCP server exposing all tools to local LLM agents

```python
# src/corpus_callosum/mcp_server/server.py
from mcp import Server
from .registry import get_registered_tools

def create_mcp_server() -> Server:
    """Create MCP server with all registered tools"""
    server = Server("corpus-callosum")
    
    # Register all tools from registry
    for tool_name, tool_func, tool_schema in get_registered_tools():
        server.add_tool(
            name=tool_name,
            func=tool_func,
            schema=tool_schema
        )
    
    return server

def main():
    """Start MCP server"""
    server = create_mcp_server()
    server.run(host="localhost", port=8765)

if __name__ == '__main__':
    main()
```

#### Dual Access Pattern

Users can:

1. **Direct CLI usage**: `corpus-flashcards -c notes`
2. **MCP via agent**: Agent calls `generate_flashcards(collection="notes")` through MCP server

Both paths use the same underlying implementation, ensuring consistency.

---

### 5. Orchestrations

Pre-composed workflows combining multiple tools:

```python
# src/corpus_callosum/orchestrations/study_session.py
from corpus_callosum.tools.flashcards.generator import FlashcardGenerator
from corpus_callosum.tools.summaries.generator import SummaryGenerator
from corpus_callosum.tools.quizzes.generator import QuizGenerator

class StudySessionOrchestrator:
    """Combines flashcards, summaries, and quizzes for comprehensive study"""
    
    def __init__(self, config: BaseConfig):
        self.flashcard_gen = FlashcardGenerator(config.flashcards)
        self.summary_gen = SummaryGenerator(config.summaries)
        self.quiz_gen = QuizGenerator(config.quizzes)
    
    def create_session(self, collection: str, topic: str) -> dict:
        """Generate complete study materials"""
        return {
            "summary": self.summary_gen.generate(collection, topic),
            "flashcards": self.flashcard_gen.generate(collection, topic),
            "quiz": self.quiz_gen.generate(collection, topic)
        }
```

Orchestrations are also exposed via CLI and MCP for agent usage.

---

## Implementation Plan

### Phase 1: Foundation (Week 1-2) ✅ **COMPLETED**

#### Tasks
- [x] Design and implement configuration system
  - [x] Create `BaseConfig` dataclass hierarchy
  - [x] Implement YAML loader with deep merge
  - [x] Add environment variable override support
  - [x] Write unit tests for config loading
- [x] Create database abstraction layer
  - [x] Define `DatabaseBackend` interface
  - [x] Implement `ChromaDBBackend`
  - [x] Add collection namespacing
  - [x] Write integration tests
- [x] Set up project structure
  - [x] Create directory layout
  - [x] Configure `pyproject.toml`
  - [x] Set up pytest framework
  - [x] Configure linting (ruff) and type checking (mypy)

**Deliverables**: ✅
- Working configuration system with tests
- Database abstraction with ChromaDB implementation
- Project skeleton with build configuration

**Git Commit**: `3b2bd5e` - "feat: Implement Phase 1 foundation"

---

### Phase 2: Tool Migration (Week 3-4) ✅ **COMPLETED**

#### Tasks
- [x] Migrate RAG functionality
  - [x] Move existing RAG code to `tools/rag/`
  - [x] Create `RAGConfig` dataclass
  - [x] Refactor to use database abstraction
  - [x] Update CLI interface
  - [x] Add MCP wrapper
  - [x] Write tests
- [x] Separate flashcard/summary/quiz tools
  - [x] Extract flashcard logic to `tools/flashcards/`
  - [x] Extract summary logic to `tools/summaries/`
  - [x] Extract quiz logic to `tools/quizzes/`
  - [x] Create individual config classes
  - [x] Build CLI interfaces for each
  - [x] Add MCP wrappers
  - [x] Write tests
- [x] Migrate video transcription
  - [x] Move to `tools/video/`
  - [x] Create `VideoConfig` dataclass
  - [x] Integrate with database abstraction
  - [x] Update CLI interface
  - [x] Add MCP wrapper
  - [x] Write tests

**Deliverables**: ✅
- All tools migrated and working independently
- Individual CLI commands for each tool
- Comprehensive test coverage

**Git Commit**: `428e6db` - "feat: Implement Phase 2 - Tool Migration"

---

### Phase 3: MCP Server & Orchestrations (Week 5-6) ✅ **COMPLETED**

#### Tasks
- [x] Implement MCP server
  - [x] Create tool registry system
  - [x] Build MCP server with tool registration (FastMCP implementation)
  - [x] Add request/response handling
  - [x] Implement error handling
  - [x] Add logging and monitoring
- [x] Create MCP tool wrappers
  - [x] Wrap each tool with MCP interface
  - [x] Define tool schemas
  - [x] Add parameter validation
  - [x] Write integration tests
- [x] Build pre-composed workflows (orchestrations)
  - [x] Study session (flashcards + summaries + quiz)
  - [x] Lecture processing (video → transcription → RAG → flashcards)  
  - [x] Knowledge base building (ingest → index → query)
- [x] Add orchestration CLI commands
- [x] Expose orchestrations via MCP
- [x] Test with local LLM
  - [x] Set up test harness with MCP
  - [x] Verify tool calling works
  - [x] Test error scenarios
  - [x] Document MCP usage

**Deliverables**: ✅
- Working MCP server with FastMCP framework
- All tools accessible via MCP (9 tools, 2 resources, 2 prompts)
- Working orchestrations with CLI and MCP access
- Integration tests and documentation
- Server running on `http://localhost:8000/mcp`

**Git Commit**: `cddcc87` - "feat: Implement Phase 3 - MCP Server & Orchestrations"

**Implementation Notes**:
- Combined Phase 3 (MCP Server) and Phase 4 (Orchestrations) due to architectural synergies
- Used FastMCP framework for rapid MCP tool exposure
- All tools have placeholder LLM implementations (to be completed in Phase 4: LLM Integration)
- Version bumped to 0.4.0 to reflect major milestone completion

---

### Phase 4: LLM Integration & Enhancement (Week 7) ✅ **COMPLETED**

#### Tasks
- [x] Replace placeholder LLM implementations
  - [x] Implement actual LLM generation for flashcards
  - [x] Implement actual LLM generation for summaries  
  - [x] Implement actual LLM generation for quizzes
  - [x] Add support for multiple LLM backends (Ollama, OpenAI, Claude)
- [x] Enhance RAG functionality
  - [x] Add LLM-powered response generation
  - [x] Implement context-aware prompting
  - [x] Add foundation for conversation memory
- [x] Advanced features
  - [x] Add professional prompt template system
  - [x] Implement robust response parsing
  - [x] Add comprehensive error handling and fallbacks

**Deliverables**: ✅
- Fully functional LLM integration across all tools
- Multi-backend LLM support (Ollama, OpenAI, Anthropic)
- Professional prompt template system
- Enhanced RAG with context-aware responses
- Comprehensive error handling and fallbacks

**Git Commit**: TBD - "feat: Implement Phase 4 - LLM Integration & Enhancement"

**Implementation Notes**:
- Created new `corpus_callosum.llm` module with unified backend abstraction
- Added `PromptTemplates` class with standardized prompts for all content types
- Enhanced all tool generators with actual LLM-powered content creation
- Implemented robust parsing and fallback mechanisms
- Version bumped to 0.5.0 to reflect major functionality milestone
- Maintained full backward compatibility while adding powerful new capabilities

---

### Phase 5: Docker & Deployment (Week 8) ✅ **COMPLETED**

#### Tasks
- [x] Consolidate Docker configuration
  - [x] Single `Dockerfile` for all services
  - [x] Update `docker-compose.yml` with:
    - ChromaDB service
    - MCP server service
    - OpenTelemetry collector (optional)
  - [x] Add health checks
  - [x] Configure networking
- [x] Database management
  - [x] Add backup/restore utilities
  - [x] Implement collection migration tools
  - [x] Add data export functionality
- [x] Deployment documentation
  - [x] Docker setup guide
  - [x] Configuration examples
  - [x] Troubleshooting guide

**Deliverables**: ✅
- Production-ready Docker setup with multi-stage builds
- Comprehensive docker-compose with profiles for different deployment scenarios  
- Database management CLI with backup/restore/migration/export functionality
- Complete deployment documentation with troubleshooting guide
- Health checks and observability integration

**Git Commit**: TBD - "feat: Implement Phase 5 - Docker & Deployment"

**Implementation Notes**:
- Created unified multi-stage Dockerfile with development, production, and CLI targets
- Implemented comprehensive docker-compose.yml with service profiles for flexible deployment
- Added health checks and monitoring with OpenTelemetry and Jaeger integration
- Built complete database management utility with backup, restore, migration, and export features
- Created extensive documentation covering deployment, configuration, and troubleshooting
- All services properly networked with volume persistence and security considerations

---

### Phase 6: Polish & Documentation (Week 9)

#### Tasks
- [ ] Comprehensive documentation
  - [ ] Architecture overview
  - [ ] Configuration guide
  - [ ] Tool usage documentation
  - [ ] MCP integration guide
  - [ ] API reference
- [ ] Examples and tutorials
  - [ ] Getting started guide
  - [ ] Common workflows
  - [ ] Advanced configuration
  - [ ] Troubleshooting
- [ ] Performance optimization
  - [ ] Profile critical paths
  - [ ] Optimize database queries
  - [ ] Add caching where appropriate
- [ ] Final testing
  - [ ] End-to-end testing
  - [ ] Load testing
  - [ ] Security audit

**Deliverables**:
- Complete documentation
- Optimized performance
- Production-ready release

---

## Technology Stack

### Core Dependencies

**Essential** (keep minimal):
- `fastapi` - REST API framework (if needed for web interface)
- `chromadb` - Vector database
- `sentence-transformers` - Embeddings (or use Ollama)
- `pyyaml` - Configuration
- `click` - CLI framework
- `httpx` - HTTP client for LLM calls
- `python-dotenv` - Environment management

**Document Processing**:
- `pypdf` - PDF parsing
- `python-docx` - Word documents
- `beautifulsoup4` + `markdownify` - HTML to Markdown
- `striprtf` - RTF parsing

**Video Transcription**:
- `faster-whisper` - Efficient Whisper implementation
- `ffmpeg-python` - Video processing (wrapper for system ffmpeg)

**Development**:
- `pytest` + `pytest-cov` - Testing
- `ruff` - Linting
- `mypy` - Type checking

**Optional** (via extras):
- `opentelemetry-*` - Observability (install via `[observability]`)

### MCP Integration

Use the official MCP Python SDK:
```bash
pip install mcp
```

For local LLM integration, configure with Ollama or similar.

---

## Configuration Management

### Hierarchy

1. **Base Config** (`configs/base.yaml`): Shared settings
2. **Tool Configs** (`configs/<tool>.yaml`): Tool-specific overrides
3. **Environment Variables**: Runtime overrides (`CC_*` prefix)
4. **CLI Arguments**: Highest precedence

### Merge Strategy

```python
# Pseudocode
base_config = load_yaml("configs/base.yaml")
tool_config = load_yaml(f"configs/{tool}.yaml")
merged = deep_merge(base_config, tool_config)
env_overrides = parse_env_vars(prefix="CC_")
final_config = deep_merge(merged, env_overrides)
cli_overrides = parse_cli_args()
final_config = deep_merge(final_config, cli_overrides)
```

### Example

```bash
# Base config has llm.model = "llama3"
# flashcards.yaml has llm.model = "llama3.2"
# Environment: CC_LLM_MODEL=mistral
# CLI: --llm-model qwen3

# Final: qwen3 (CLI wins)
```

---

## Database Strategy

### Single Database Instance

Run one ChromaDB instance (Docker or persistent) shared across all tools.

### Collection Namespacing

| Tool | Collection Pattern | Example |
|------|-------------------|---------|
| Flashcards | `flashcards_<topic>` | `flashcards_biology` |
| Summaries | `summaries_<topic>` | `summaries_history` |
| Quizzes | `quizzes_<topic>` | `quizzes_math` |
| RAG | `rag_<name>` | `rag_lecture_notes` |
| Video | `video_<course>` | `video_cs101` |

### Metadata Strategy

Store tool-specific metadata in collection metadata:

```python
collection_metadata = {
    "tool": "flashcards",
    "created_at": "2026-04-07T10:00:00Z",
    "created_by": "user",
    "topic": "biology",
    "difficulty": "intermediate",
    "version": "1.0"
}
```

### Data Sync

Abstract sync functionality in `db/sync.py`:

```python
def sync_collections(
    source_backend: DatabaseBackend,
    target_backend: DatabaseBackend,
    collection_pattern: str
) -> None:
    """Sync collections matching pattern between backends"""
    pass
```

This enables:
- Local ↔ Remote sync
- Backup/restore
- Collection migration

---

## MCP Architecture

### Server Design

Single MCP server exposing all tools as callable functions.

```python
# Start MCP server
corpus-mcp-server

# Or via Python module
python -m corpus_callosum mcp-server
```

### Tool Registration

Tools self-register on import:

```python
# Each tool's mcp.py
from corpus_callosum.mcp_server.registry import register_tool

@register_tool(...)
def my_tool(...):
    pass
```

Server discovers all registered tools at startup.

### Agent Integration

Agents interact via standard MCP protocol:

```json
{
  "method": "tools/call",
  "params": {
    "name": "generate_flashcards",
    "arguments": {
      "collection": "biology",
      "count": 15,
      "difficulty": "advanced"
    }
  }
}
```

### Dual Access Guarantee

Every MCP tool has a corresponding CLI command:

```bash
# Via CLI
corpus-flashcards -c biology --count 15 --difficulty advanced

# Via MCP (agent)
generate_flashcards(collection="biology", count=15, difficulty="advanced")
```

Both use the same underlying implementation.

---

## Testing Strategy

### Unit Tests

Test individual components in isolation:

```python
# tests/unit/test_flashcards.py
def test_flashcard_generation():
    config = FlashcardConfig(cards_per_topic=5)
    generator = FlashcardGenerator(config)
    cards = generator.generate("test_collection")
    assert len(cards) == 5
```

### Integration Tests

Test component interactions:

```python
# tests/integration/test_cli.py
def test_flashcard_cli(tmp_path):
    result = run_cli([
        "corpus-flashcards",
        "-c", "test",
        "-o", str(tmp_path / "cards.txt")
    ])
    assert result.exit_code == 0
    assert (tmp_path / "cards.txt").exists()
```

### MCP Tests

Test MCP server and tool calling:

```python
# tests/integration/test_mcp_server.py
def test_mcp_flashcard_tool():
    server = create_mcp_server()
    result = server.call_tool(
        "generate_flashcards",
        {"collection": "test", "count": 5}
    )
    assert result["status"] == "success"
    assert len(result["cards"]) == 5
```

### End-to-End Tests

Test complete workflows:

```python
# tests/integration/test_orchestrations.py
def test_study_session_workflow():
    orchestrator = StudySessionOrchestrator(config)
    session = orchestrator.create_session("biology", "photosynthesis")
    assert "summary" in session
    assert "flashcards" in session
    assert "quiz" in session
```

---

## Migration Strategy

### Phase 1: Preserve Existing Functionality

1. Copy existing code to new structure
2. Update imports and paths
3. Ensure all existing features work
4. Run existing tests (if any)

### Phase 2: Refactor to New Architecture

1. Extract configuration to dataclasses
2. Migrate to database abstraction
3. Create CLI wrappers
4. Add MCP wrappers
5. Write new tests

### Phase 3: Consolidate

1. Remove duplicate code
2. Standardize interfaces
3. Update documentation
4. Remove old directory structures

### Backward Compatibility

During migration, maintain compatibility:

```bash
# Old way (deprecated but working)
cd flashcards_summaries_quizzes && python src/__main__.py

# New way
corpus-flashcards -c notes
```

Add deprecation warnings to old entry points.

---

## Open Questions & Decisions

### 1. MCP Server vs. REST API

**Options**:
- **Option A**: MCP server only (simpler, agent-focused)
- **Option B**: Both MCP and REST API (more flexible, web UI possible)
- **Option C**: MCP server + FastAPI for observability/monitoring

**Recommendation**: Start with **Option A** (MCP only), add REST API later if needed.

### 2. Embedding Strategy

**Options**:
- **Option A**: Ollama embeddings (unified with LLM)
- **Option B**: sentence-transformers (more models, offline)
- **Option C**: Support both (configurable)

**Recommendation**: **Option C** (already implemented in RAG, extend to other tools)

### 3. Database per Tool vs. Shared Database

**Options**:
- **Option A**: Separate ChromaDB instances per tool
- **Option B**: Single ChromaDB with namespaced collections

**Recommendation**: **Option B** (simpler deployment, shared resources)

### 4. CLI Framework

**Options**:
- **Option A**: `click` (current in RAG)
- **Option B**: `argparse` (stdlib)
- **Option C**: `typer` (modern, type-based)

**Recommendation**: **Option A** (`click` - already used, proven, flexible)

### 5. Docker Strategy

**Options**:
- **Option A**: Single container with all tools
- **Option B**: Separate containers per tool
- **Option C**: Hybrid (shared DB, separate tool services)

**Recommendation**: **Option A** initially, **Option C** for production scaling

---

## Success Metrics

### Functionality
- [ ] All tools runnable via CLI
- [ ] All tools accessible via MCP
- [ ] Orchestrations working end-to-end
- [ ] Database sync functional

### Quality
- [ ] >80% test coverage
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] No critical security issues

### Performance
- [ ] Flashcard generation: <5s for 10 cards
- [ ] RAG query: <3s for response
- [ ] Video transcription: <0.5x realtime
- [ ] MCP tool call overhead: <100ms

### User Experience
- [ ] CLI intuitive and consistent
- [ ] Documentation complete and clear
- [ ] Error messages helpful
- [ ] Setup process <5 minutes

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| MCP SDK instability | High | Medium | Pin versions, test thoroughly |
| ChromaDB performance issues | Medium | Low | Benchmark early, consider alternatives |
| Configuration complexity | Medium | Medium | Provide good examples, validation |
| Migration data loss | High | Low | Backup before migration, test thoroughly |

### Dependency Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| faster-whisper breaking changes | Medium | Low | Pin version, monitor releases |
| Ollama API changes | Medium | Medium | Abstract LLM interface |
| ChromaDB compatibility | High | Low | Use stable API subset |

### User Experience Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Confusing CLI interface | High | Medium | User testing, clear documentation |
| MCP setup complexity | High | Medium | Detailed guide, automated setup |
| Configuration errors | Medium | High | Validation, helpful error messages |

---

## Future Enhancements

### Short-term (3-6 months)
- [ ] Web UI for RAG queries and flashcard review
- [ ] Spaced repetition scheduling for flashcards
- [ ] Multi-language support for video transcription
- [ ] Cloud sync for collections (S3, Google Drive)

### Medium-term (6-12 months)
- [ ] Mobile app for flashcard review
- [ ] Collaborative features (shared collections)
- [ ] Advanced analytics (study patterns, progress tracking)
- [ ] Plugin system for custom tools

### Long-term (12+ months)
- [ ] Self-hosted web service
- [ ] Multi-user support with authentication
- [ ] Real-time collaboration
- [ ] Marketplace for shared collections

---

## Conclusion

This architecture provides a solid foundation for CorpusCallosum as a unified, modular learning and knowledge management toolkit. The design emphasizes:

1. **Modularity**: Each tool independent and reusable
2. **Dual Access**: CLI and MCP for maximum flexibility
3. **Configuration**: Hierarchical, overridable, type-safe
4. **Database**: Single instance, clean abstraction
5. **Testing**: Comprehensive coverage at all levels
6. **Documentation**: Clear, complete, maintainable

By following this plan, we'll create a well-engineered system that serves both direct CLI usage and agent orchestration, with minimal dependencies and maximum maintainability.

---

## Appendix A: CLI Command Reference

```bash
# Core tools
corpus-flashcards -c <collection> [--output FILE] [--count N]
corpus-summaries -c <collection> [--output FILE] [--topic TOPIC]
corpus-quizzes -c <collection> [--output FILE] [--difficulty LEVEL]
corpus-rag query -c <collection> -q <question> [--top-k N]
corpus-rag ingest -p <path> -c <collection>
corpus-video transcribe -i <video> [--model MODEL]
corpus-video clean -i <transcript> [--model MODEL]

# Orchestrations
corpus-study-session -c <collection> -t <topic>
corpus-lecture-pipeline -i <video> --course <name> --lecture <num>
corpus-knowledge-base build -p <path> -c <collection>

# Utilities
corpus-config validate [--config FILE]
corpus-config show [--tool TOOL]
corpus-db list-collections
corpus-db backup -c <collection> -o <file>
corpus-db restore -i <file>
corpus-mcp-server [--port PORT]
```

---

## Appendix B: Configuration Examples

### Minimal Configuration

```yaml
# configs/base.yaml
llm:
  endpoint: http://localhost:11434
  model: llama3

database:
  mode: persistent
  persist_directory: ./chroma_store
```

### Advanced Configuration

```yaml
# configs/base.yaml
llm:
  endpoint: http://localhost:11434
  model: llama3
  timeout_seconds: 180.0
  temperature: 0.7
  max_tokens: 2048

embedding:
  backend: ollama
  model: nomic-embed-text

database:
  backend: chromadb
  mode: http
  host: localhost
  port: 8000

paths:
  vault: ~/Documents/vault
  scratch_dir: ~/.cache/corpus-callosum
  output_dir: ~/Documents/corpus-output

observability:
  enabled: true
  otlp_endpoint: http://localhost:4317
  service_name: corpus-callosum
```

### Tool-Specific Override

```yaml
# configs/video.yaml
llm:
  model: qwen3:8b  # Better for transcript cleaning
  temperature: 0.5

video:
  transcription:
    model: medium.en
    device: cuda
    compute_type: float16
    language: en
  cleaning:
    model: qwen3:8b
    prompt_template: |
      Clean the following transcript...
      {transcript}
```

---

## Appendix C: MCP Tool Schemas

### Flashcard Generation

```json
{
  "name": "generate_flashcards",
  "description": "Generate flashcards from a knowledge collection",
  "parameters": {
    "type": "object",
    "properties": {
      "collection": {
        "type": "string",
        "description": "Collection name to generate flashcards from"
      },
      "count": {
        "type": "integer",
        "description": "Number of flashcards to generate",
        "default": 10,
        "minimum": 1,
        "maximum": 100
      },
      "difficulty": {
        "type": "string",
        "enum": ["basic", "intermediate", "advanced"],
        "description": "Difficulty level of flashcards",
        "default": "intermediate"
      },
      "topic": {
        "type": "string",
        "description": "Specific topic to focus on (optional)"
      }
    },
    "required": ["collection"]
  }
}
```

### RAG Query

```json
{
  "name": "rag_query",
  "description": "Query knowledge base using RAG",
  "parameters": {
    "type": "object",
    "properties": {
      "collection": {
        "type": "string",
        "description": "Collection to query"
      },
      "query": {
        "type": "string",
        "description": "Question to answer"
      },
      "top_k": {
        "type": "integer",
        "description": "Number of results to retrieve",
        "default": 10,
        "minimum": 1,
        "maximum": 50
      },
      "session_id": {
        "type": "string",
        "description": "Session ID for multi-turn conversation (optional)"
      }
    },
    "required": ["collection", "query"]
  }
}
```

### Video Transcription

```json
{
  "name": "transcribe_video",
  "description": "Transcribe video to text using Whisper",
  "parameters": {
    "type": "object",
    "properties": {
      "video_path": {
        "type": "string",
        "description": "Path to video file or directory of segments"
      },
      "output_path": {
        "type": "string",
        "description": "Output path for transcript (optional)"
      },
      "model": {
        "type": "string",
        "enum": ["tiny", "base", "small", "medium", "large-v3"],
        "description": "Whisper model size",
        "default": "medium"
      },
      "language": {
        "type": "string",
        "description": "Language code (e.g., 'en', 'es') or null for auto-detect",
        "default": "en"
      },
      "clean": {
        "type": "boolean",
        "description": "Apply LLM-based cleaning after transcription",
        "default": false
      }
    },
    "required": ["video_path"]
  }
}
```

---

**End of Architecture Plan**
