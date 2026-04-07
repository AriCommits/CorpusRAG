# Docker Deployment Guide

This guide covers deploying CorpusCallosum using Docker and Docker Compose.

## 🚀 Quick Start

### Minimal Deployment (ChromaDB + MCP Server)

```bash
# Clone the repository
git clone <repository-url>
cd CorpusCallosum

# Start minimal services
docker compose -f .docker/docker-compose.yml up chromadb corpus-mcp
```

The MCP server will be available at `http://localhost:8000`.

### Full Stack Deployment

```bash
# Start all services including Ollama and observability
docker compose -f .docker/docker-compose.yml --profile full up -d
```

Services:
- **MCP Server**: `http://localhost:8000`
- **ChromaDB**: `http://localhost:8001`
- **Ollama**: `http://localhost:11434`
- **Jaeger UI**: `http://localhost:16686`
- **Prometheus Metrics**: `http://localhost:8888`

## 📋 Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available
- 10GB free disk space (for models and data)

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Ollama        │    │  CorpusCallosum  │    │   ChromaDB      │
│   (LLM)         │◄───┤   MCP Server     ├───►│   (Vector DB)   │
│   :11434        │    │   :8000          │    │   :8001         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │
                       ┌───────┴────────┐
                       │  Observability │
                       │  (Optional)    │
                       │  Jaeger/OTEL   │
                       └────────────────┘
```

## 🔧 Configuration

### Environment Variables

Common environment variables for configuration:

```bash
# Database
CC_DATABASE_MODE=http
CC_DATABASE_HOST=chromadb
CC_DATABASE_PORT=8000

# LLM Configuration
CC_LLM_ENDPOINT=http://ollama:11434
CC_LLM_MODEL=llama3
CC_LLM_TEMPERATURE=0.7

# Paths
CC_PATHS_VAULT=/home/corpus/data/vault
CC_PATHS_OUTPUT_DIR=/home/corpus/data/output
```

### Configuration Files

Use configuration files for more complex setups:

```yaml
# configs/docker.yaml
llm:
  endpoint: http://ollama:11434
  model: llama3
  temperature: 0.7

database:
  backend: chromadb
  mode: http
  host: chromadb
  port: 8000
```

Mount configuration:

```bash
docker run -v ./configs:/home/corpus/app/configs corpus-callosum
```

## 🏃 Running Different Profiles

### Development Mode

```bash
# With hot reload and debug logging
docker compose \
  -f .docker/docker-compose.yml \
  -f .docker/docker-compose.dev.yml \
  --profile full up
```

### CLI Tools Only

```bash
# Interactive container for CLI usage
docker compose --profile cli up corpus-cli

# Or run specific commands
docker compose run --rm corpus-cli corpus-rag ingest --path /data/docs --collection notes
```

### With Local LLM

```bash
# Include Ollama service
docker compose --profile ollama up

# Pull and run a model
docker compose exec ollama ollama pull llama3
```

### With Observability

```bash
# Include monitoring stack
docker compose --profile observability up
```

## 📁 Volume Mounts

### Persistent Data

```yaml
volumes:
  # Application data
  - corpus-data:/home/corpus/data
  
  # Configuration (read-only)
  - ./configs:/home/corpus/app/configs:ro
  
  # User documents
  - ./vault:/home/corpus/data/vault:rw
```

### Local Development

```yaml
volumes:
  # Source code (for hot reload)
  - ./src:/home/corpus/app/src:rw
  - ./tests:/home/corpus/app/tests:rw
```

## 🔍 Health Checks

All services include comprehensive health checks:

```bash
# Check service health
docker compose ps

# View health check logs
docker compose logs corpus-mcp
```

### Manual Health Check

```bash
# Test MCP server
curl http://localhost:8000/health

# Test ChromaDB
curl http://localhost:8001/api/v1/heartbeat

# Test Ollama
curl http://localhost:11434/api/tags
```

## 🛠️ Database Management

### Backup Collections

```bash
# Backup a specific collection
docker compose exec corpus-mcp corpus-db backup notes --output /data/backups/notes.tar.gz

# Backup all collections
docker compose exec corpus-mcp corpus-db backup-all --output-dir /data/backups
```

### Restore Collections

```bash
# Restore from backup
docker compose exec corpus-mcp corpus-db restore /data/backups/notes.tar.gz --name notes_restored
```

### Export Data

```bash
# Export collection to JSON
docker compose exec corpus-mcp corpus-db export notes --output /data/exports/notes.json --format json
```

## 🔧 Customization

### Custom Dockerfile Targets

```bash
# Build specific target
docker build -f .docker/Dockerfile --target cli -t corpus-cli .
docker build -f .docker/Dockerfile --target development -t corpus-dev .
```

### Custom Compose Override

```yaml
# docker-compose.override.yml
version: '3.8'

services:
  corpus-mcp:
    environment:
      - CC_LLM_MODEL=mistral
    ports:
      - "8080:8000"  # Custom port
```

## 📊 Monitoring

### Prometheus Metrics

```bash
# Access Prometheus metrics
curl http://localhost:8889/metrics
```

### Jaeger Tracing

Visit `http://localhost:16686` for distributed tracing.

### Logs

```bash
# View all logs
docker compose logs -f

# Service-specific logs
docker compose logs -f corpus-mcp
docker compose logs -f chromadb
docker compose logs -f ollama
```

## 🚨 Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs
docker compose logs <service-name>

# Verify health
docker compose ps
```

**Out of memory:**
```bash
# Increase Docker memory limit
# Check resource usage
docker stats
```

**Port conflicts:**
```bash
# Check what's using ports
netstat -tlnp | grep :8000
```

**Permission issues:**
```bash
# Fix volume permissions
docker compose exec corpus-mcp chown -R corpus:corpus /home/corpus/data
```

### Reset Everything

```bash
# Stop all services
docker compose down

# Remove volumes (WARNING: destroys data)
docker compose down -v

# Remove all containers and images
docker compose down --rmi all
```

## 🔒 Production Considerations

### Security

1. **Use secrets for API keys:**
```bash
echo "your-api-key" | docker secret create ollama_api_key -
```

2. **Run as non-root:** (Already configured in Dockerfile)

3. **Limit resources:**
```yaml
services:
  corpus-mcp:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

### Performance

1. **Use external ChromaDB for scale**
2. **Configure persistent volumes with appropriate drivers**
3. **Set up load balancing for multiple MCP instances**

### Backup Strategy

```bash
# Automated backups with cron
0 2 * * * docker compose exec corpus-mcp corpus-db backup-all --output-dir /backups/$(date +%Y%m%d)
```

## 📚 Additional Resources

- [CorpusCallosum Architecture](../README.md)
- [Configuration Guide](../configs/README.md)
- [MCP Integration](./mcp-integration.md)
- [Development Setup](./development.md)