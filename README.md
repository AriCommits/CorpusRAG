# CorpusCallosum

CorpusCallosum is a local-first RAG service with:

- one ChromaDB store and many named collections,
- hybrid retrieval (semantic + BM25 + RRF),
- local model generation (Ollama-compatible `/api/generate`),
- API endpoints for ingest, query, critique, flashcards, and collection listing.
- built-in security (rate limiting, API key auth),
- OpenTelemetry observability with Jaeger tracing.

## Project layout

```text
src/corpus_callosum/
  __init__.py
  config.py
  ingest.py
  retriever.py
  agent.py
  api.py
  security.py
  observability.py
  setup.py

configs/
  corpus_callosum.yaml.example
  corpus_callosum.docker.yaml.example

.docker/
  Dockerfile
  docker-compose.yml
  otel-collector-config.yaml

tests/
  test_smoke.py
  test_agent.py
  test_api.py
  test_config.py
  test_ingest.py
  test_observability.py
  test_retriever.py
  test_security.py
```

## Requirements

- Python 3.11+
- Local model runner endpoint (default: Ollama at `http://localhost:11434/api/generate`)

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Configuration

Copy the example config:

```bash
cp configs/corpus_callosum.yaml.example configs/corpus_callosum.yaml
```

Config is loaded from:

- `CORPUS_CALLOSUM_CONFIG` environment variable, or
- `configs/corpus_callosum.yaml` by default.

## Running

Start API server:

```bash
PYTHONPATH=src python3 -m corpus_callosum.api
```

Or with installed package script:

```bash
corpus-api
```

### Endpoints

- `GET /health`
- `GET /rate-limit` - Check rate limit status
- `POST /ingest` body: `{ "file_path": "./vault/bio201", "collection": "bio201" }`
- `POST /query` body: `{ "query": "What is photosynthesis?", "collection": "bio201" }` (SSE stream)
- `POST /critique` body: `{ "essay_text": "..." }` (SSE stream)
- `POST /flashcards` body: `{ "collection": "bio201" }` (SSE stream)
- `GET /collections`

### API Documentation

Interactive API docs are available at:

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- OpenAPI JSON: `http://localhost:8080/openapi.json`

## CLI ingest

```bash
PYTHONPATH=src python3 -m corpus_callosum.ingest --path ./vault/bio201 --collection bio201
```

## Smoke test

```bash
python3 tests/test_smoke.py
```

This test creates a temporary markdown file, ingests it into a test collection, queries it, and prints the streamed response.

## Security

### Rate Limiting

Rate limiting is enabled by default:

- 10 requests per second (burst)
- 60 requests per minute
- 1,000 requests per hour

Configure in your YAML:

```yaml
security:
  rate_limit_enabled: true
  requests_per_minute: 60
  requests_per_hour: 1000
  burst_limit: 10
```

### API Key Authentication

Enable API key auth:

```yaml
security:
  auth_enabled: true
  api_keys:
    - your-secret-key-here
```

Then include the key in requests:

```bash
curl -H "X-API-Key: your-secret-key-here" http://localhost:8080/health
```

## Docker and Observability

This repo includes Docker support for running the API, ChromaDB, and observability stack together.

Files:

- `.docker/Dockerfile` - builds the API container.
- `.docker/docker-compose.yml` - runs `corpus_api` + `chroma` + `otel-collector` + `jaeger` services.
- `.docker/otel-collector-config.yaml` - OpenTelemetry Collector configuration.
- `configs/corpus_callosum.docker.yaml.example` - config template using Chroma HTTP mode.

### Setup

Copy docker config template:

```bash
cp configs/corpus_callosum.docker.yaml.example configs/corpus_callosum.docker.yaml
```

Then start services:

```bash
docker compose -f .docker/docker-compose.yml up --build
```

### Notes

- Chroma runs at `chroma:8000` inside compose and `localhost:8000` on host.
- API runs at `localhost:8080`.
- Docker config sets:
  - `chroma.mode: http`
  - `chroma.host: chroma`
  - `chroma.port: 8000`
- Model endpoint in the docker config points to host Ollama by default:
  - `http://host.docker.internal:11434/api/generate`

### Observability Stack

The Docker compose includes an observability stack:

- **OpenTelemetry Collector** (`otel-collector:4317`) - receives and processes traces
- **Jaeger** (`jaeger:16686`) - trace visualization UI

Access the Jaeger UI at `http://localhost:16686` to view RAG query traces, LLM call metrics, and request flows.

Enable observability in your config:

```yaml
observability:
  enabled: true
  otlp_endpoint: http://otel-collector:4317
  openllmetry_enabled: true
```

## Examples

### Ingest a directory

```bash
curl -X POST http://localhost:8080/ingest \
  -H "Content-Type: application/json" \
  -d '{"file_path": "./vault/biology", "collection": "biology101"}'
```

### Query a collection

```bash
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is photosynthesis?", "collection": "biology101"}'
```

### Generate flashcards

```bash
curl -X POST http://localhost:8080/flashcards \
  -H "Content-Type: application/json" \
  -d '{"collection": "biology101"}'
```

### List collections

```bash
curl http://localhost:8080/collections
```

## Tutorial: Integrating with Local Knowledge Bases

### 1. Prepare your documents

Place your documents (PDF, Markdown, TXT) in the `vault/` directory:

```bash
mkdir -p vault/my-knowledge
cp ~/Documents/notes/*.md vault/my-knowledge/
```

### 2. Ingest your documents

```bash
curl -X POST http://localhost:8080/ingest \
  -H "Content-Type: application/json" \
  -d '{"file_path": "./vault/my-knowledge", "collection": "my-notes"}'
```

### 3. Query your knowledge base

```bash
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What did I learn about machine learning?", "collection": "my-notes"}'
```

### 4. Generate study flashcards

```bash
curl -X POST http://localhost:8080/flashcards \
  -H "Content-Type: application/json" \
  -d '{"collection": "my-notes"}'
```

## Troubleshooting

### Ollama not running

**Error**: `404 Not Found` for `http://localhost:11434/api/generate`

**Solution**: Start Ollama and pull a model:

```bash
ollama serve
ollama pull llama3
```

### Config file not found

**Error**: `Configuration file not found at ...`

**Solution**: Copy the example config:

```bash
cp configs/corpus_callosum.yaml.example configs/corpus_callosum.yaml
```

### Docker: Cannot connect to Ollama

**Solution**: The Docker config uses `host.docker.internal` to reach Ollama on your host. Ensure Ollama is running and accessible.

### ChromaDB connection refused

**Solution**: If running locally (not Docker), set `chroma.mode: persistent` in your config. For Docker, ensure the compose stack is running.

### Import errors for observability

**Error**: `Observability enabled but opentelemetry not installed`

**Solution**: Install observability dependencies:

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp \
  opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-httpx
```

## MCP (Model Context Protocol)

CorpusCallosum exposes its capabilities as an MCP server, allowing AI clients like Claude Desktop, Cursor, and Windsurf to directly interact with your knowledge base.

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `query_documents` | Query a collection with RAG |
| `ingest_documents` | Ingest files/directories into a collection |
| `list_collections` | List all available collections |
| `critique_writing` | Get AI writing feedback |
| `generate_flashcards` | Generate study flashcards |
| `summarize_collection` | Summarize collection content |

### MCP Resources

| Resource | URI Template |
|----------|-------------|
| Collection contents | `collection://{name}` |
| Collection metadata | `collection://{name}/meta` |

### Setup

Install the MCP dependency:

```bash
pip install corpus-callosum[mcp]
```

### Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "corpus-callosum": {
      "command": "corpus-mcp",
      "args": ["--config", "/path/to/corpus_callosum.yaml"]
    }
  }
}
```

### Cursor / Windsurf

Add an MCP server with:
- **Command**: `corpus-mcp`
- **Args**: `--config /path/to/corpus_callosum.yaml`
- **Transport**: stdio

### HTTP Transport (Remote)

For remote access, run the MCP server with HTTP transport:

```bash
corpus-mcp --transport http --host 0.0.0.0 --port 8081
```

Or enable it in your API server config:

```yaml
mcp:
  enabled: true
  transport: http
  port: 8081
```

The MCP endpoint will be available at `http://localhost:8080/mcp`.

### MCP Inspector

Test your MCP server with the official inspector:

```bash
npx -y @modelcontextprotocol/inspector
```

Then connect to `http://localhost:8081` (HTTP mode) or run `corpus-mcp` and connect via stdio.
