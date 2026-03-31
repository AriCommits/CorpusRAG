# Next Steps for CorpusCallosum

## Immediate Improvements (0-2 weeks)

### 1. Configuration Management
- [x] Add validation to ensure required directories exist on startup
- [x] Improve error messages when config files are missing
- [x] Consider adding a setup wizard or initialization script

### 2. Security Enhancements
- [x] Replace broad exception catches with specific exceptions
- [x] Add input validation for file paths to prevent directory traversal
- [x] Add rate limiting to API endpoints
- [x] Add basic authentication option for API

### 3. Docker & Deployment
- [x] Create actual config files from examples in the repository (with .gitignore protection)
- [x] Improve docker-compose.yml with health checks
- [x] Add documentation for production deployment considerations
- [x] Consider adding TLS support for production

### 4. Testing & Quality
- [x] Expand test coverage beyond smoke test
- [x] Add unit tests for individual components
- [x] Add integration tests for API endpoints
- [x] Set up CI/CD pipeline (GitHub Actions)
- [x] Add linting and formatting checks (ruff, black, mypy)

### 5. Documentation
- [x] Improve README with troubleshooting section
- [x] Add API documentation (OpenAPI/Swagger)
- [x] Add examples for common use cases
- [x] Create tutorial for integrating with local knowledge bases

### 6. Observability Container
- [x] Add OpenTelemetry Collector container to docker-compose
- [x] Add Jaeger container for trace visualization
- [x] Configure OTLP exporter for RAG query logging
- [x] Update docker config to enable observability by default

## Medium-term Features (1-3 months)

### Implementation Order

#### Phase 1: Model Flexibility (foundation)
- [x] Create pluggable LLM backend abstraction (Ollama, OpenAI-compatible, Anthropic-compatible)
- [x] Add per-request model selection via API
- [x] Add embedding model selection (local and remote)
- [x] Implement fallback model chain

#### Phase 2: Conversation Memory (highest user impact)
- [x] Add in-memory conversation history with session IDs
- [x] Support multi-turn follow-up queries
- [x] Add configurable context window size

#### Phase 3: OTel Metrics & Structured Logging
- [x] Add custom RAG metrics (query duration, chunk count, token usage, errors)
- [x] Add Prometheus exporter to OTel Collector
- [ ] Implement structured logging with trace context
- [ ] Enrich span context for each RAG pipeline stage
- [ ] Create Grafana dashboard JSON

#### Phase 4: Query Expansion & Summarization
- [ ] Implement query expansion via LLM-generated alternative phrasings
- [x] Add `/summarize` endpoint for collection summarization (via MCP tool)
- [ ] Add metadata filtering to retrieval

#### Phase 5: Optional Enhancements
- [ ] Web search integration (DuckDuckGo/SearXNG)
- [ ] Document topic extraction
- [ ] Agent-like capabilities for complex tasks

#### Phase 6: MCP Integration
- [x] Create MCP server with stdio transport (Claude Desktop, Cursor, Windsurf)
- [x] Create MCP server with HTTP transport (remote access)
- [x] Expose 6 tools: query_documents, ingest_documents, list_collections, critique_writing, generate_flashcards, summarize_collection
- [x] Expose 2 resources: collection contents, collection metadata
- [x] Mount MCP endpoint on existing FastAPI app
- [x] Add MCP CLI entry point (corpus-mcp)

### 1. Enhanced Retrieval
- [ ] Add reranking models for improved relevance
- [ ] Implement query expansion techniques
- [ ] Add metadata filtering capabilities
- [ ] Support for multimodal content (images, etc.)

### 2. Model Flexibility
- [ ] Support for multiple LLM backends (not just Ollama)
- [ ] Add embedding model selection
- [ ] Quantization options for local models
- [ ] GPU acceleration support

### 3. Advanced Features
- [ ] Conversation memory/context retention
- [ ] Agent-like capabilities for complex tasks
- [ ] Web search integration for up-to-date information
- [ ] Document summarization and topic extraction

### 4. Monitoring & Observability
- [ ] Add metrics collection (Prometheus)
- [ ] Implement structured logging
- [ ] Add tracing for request flows
- [ ] Create dashboard for system health

## Long-term Vision (3+ months)

### 1. Ecosystem & Integrations
- [ ] Develop plugin system for extensibility
- [ ] Integrate with popular note-taking apps (Obsidian, Logseq, etc.)
- [ ] Create mobile companion app
- [ ] Develop VS Code extension

### 2. Performance & Scale
- [ ] Implement caching layers
- [ ] Add sharding support for large collections
- [ ] Optimize for concurrent users
- [ ] Explore vector database alternatives

### 3. Research & Innovation
- [ ] Experiment with advanced RAG techniques (ReAct, etc.)
- [ ] Implement self-improving retrieval systems
- [ ] Add knowledge graph capabilities
- [ ] Explore fine-tuning options for domain adaptation