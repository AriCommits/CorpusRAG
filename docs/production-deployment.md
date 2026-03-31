# Production Deployment Guide

This guide covers deploying CorpusCallosum in a production environment.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Deployment Options](#deployment-options)
- [Docker Compose Deployment](#docker-compose-deployment)
- [Security Considerations](#security-considerations)
- [TLS/HTTPS Configuration](#tlshttps-configuration)
- [Monitoring and Health Checks](#monitoring-and-health-checks)
- [Scaling Considerations](#scaling-considerations)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker 24.0+ and Docker Compose v2
- A machine with at least 4GB RAM (8GB+ recommended for larger models)
- Storage for ChromaDB vector database
- (Optional) Reverse proxy (nginx, Caddy, Traefik) for TLS termination
- Ollama or compatible LLM endpoint

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Production Setup                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   Reverse    │────▶│  CorpusAPI   │────▶│   ChromaDB   │    │
│  │    Proxy     │     │   :8080      │     │    :8000     │    │
│  │  (TLS/443)   │     │              │     │              │    │
│  └──────────────┘     └──────┬───────┘     └──────────────┘    │
│                              │                                  │
│                              ▼                                  │
│                       ┌──────────────┐                         │
│                       │    Ollama    │                         │
│                       │   :11434     │                         │
│                       └──────────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

Best for single-server deployments. Includes health checks and automatic restarts.

### Option 2: Manual Deployment

Run components separately for more control over resources.

### Option 3: Kubernetes

For large-scale deployments requiring horizontal scaling.

## Docker Compose Deployment

### 1. Clone and Configure

```bash
git clone https://github.com/your-org/CorpusCallosum.git
cd CorpusCallosum

# Run setup wizard
python -m corpus_callosum.setup

# Or manually copy config
cp configs/corpus_callosum.docker.yaml.example configs/corpus_callosum.docker.yaml
```

### 2. Edit Production Config

Edit `configs/corpus_callosum.docker.yaml`:

```yaml
paths:
  vault: /app/vault
  chromadb_store: /app/chroma_store

model:
  # For host Ollama:
  endpoint: http://host.docker.internal:11434/api/generate
  # Or for remote Ollama:
  # endpoint: http://your-ollama-server:11434/api/generate
  name: llama3
  timeout_seconds: 180  # Increase for slower models

server:
  host: 0.0.0.0
  port: 8080

chroma:
  mode: http
  host: chroma
  port: 8000
  ssl: false
```

### 3. Start Services

```bash
# From project root
docker compose -f .docker/docker-compose.yml up -d --build

# Check status
docker compose -f .docker/docker-compose.yml ps

# View logs
docker compose -f .docker/docker-compose.yml logs -f
```

### 4. Verify Deployment

```bash
# Health check
curl http://localhost:8080/health

# List collections
curl http://localhost:8080/collections
```

## Security Considerations

### 1. Network Security

- **Do not expose ports directly to the internet** without a reverse proxy
- Use Docker networks to isolate services
- Consider using a firewall (ufw, iptables) to limit access

### 2. File Path Validation

CorpusCallosum includes built-in path traversal protection, but you should:

- Run containers with non-root users when possible
- Mount volumes as read-only where appropriate
- Limit vault directory to expected document locations

### 3. Rate Limiting

Consider adding rate limiting at the reverse proxy level:

```nginx
# nginx example
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://corpus_api:8080;
}
```

### 4. Authentication

For production deployments requiring authentication, add a reverse proxy with:

- Basic authentication
- OAuth2/OIDC integration
- API key validation

Example nginx basic auth:

```nginx
location / {
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://corpus_api:8080;
}
```

## TLS/HTTPS Configuration

### Using Caddy (Simplest)

Create `Caddyfile`:

```
corpus.yourdomain.com {
    reverse_proxy corpus_api:8080
}
```

Add to docker-compose:

```yaml
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    depends_on:
      - corpus_api

volumes:
  caddy_data:
```

### Using nginx with Let's Encrypt

```nginx
server {
    listen 443 ssl http2;
    server_name corpus.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/corpus.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/corpus.yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support
        proxy_buffering off;
        proxy_cache off;
    }
}

server {
    listen 80;
    server_name corpus.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

## Monitoring and Health Checks

### Built-in Health Checks

The Docker Compose setup includes health checks:

| Service | Endpoint | Interval |
|---------|----------|----------|
| ChromaDB | `/api/v1/heartbeat` | 30s |
| CorpusAPI | `/health` | 30s |

### External Monitoring

Monitor these endpoints:

```bash
# Basic uptime check
curl -f http://localhost:8080/health

# Response time check
curl -w "%{time_total}\n" -o /dev/null -s http://localhost:8080/health
```

### Prometheus Metrics (Future)

Prometheus metrics endpoint planned for future release.

### Log Aggregation

Collect logs from Docker:

```bash
# JSON logging for easier parsing
docker compose -f .docker/docker-compose.yml logs --no-color | jq '.'

# Or send to a log aggregator
docker compose -f .docker/docker-compose.yml logs -f | your-log-shipper
```

## Scaling Considerations

### Vertical Scaling

- **Memory**: ChromaDB performance improves with more RAM for caching
- **CPU**: Embedding generation is CPU-intensive
- **Storage**: Use SSDs for ChromaDB persistence

### Horizontal Scaling (Advanced)

For high-traffic deployments:

1. **Multiple API instances**: Load balance across multiple `corpus_api` containers
2. **ChromaDB**: Use ChromaDB's cloud offering or run a dedicated cluster
3. **Ollama**: Deploy multiple Ollama instances with load balancing

```yaml
# docker-compose.scale.yml
services:
  corpus_api:
    deploy:
      replicas: 3
```

## Backup and Recovery

### ChromaDB Data

```bash
# Stop services
docker compose -f .docker/docker-compose.yml stop

# Backup ChromaDB volume
docker run --rm -v corpus_chroma_data:/data -v $(pwd)/backup:/backup \
  alpine tar czf /backup/chroma-$(date +%Y%m%d).tar.gz /data

# Restart services
docker compose -f .docker/docker-compose.yml start
```

### Vault Documents

```bash
# Backup vault directory
tar czf vault-backup-$(date +%Y%m%d).tar.gz vault/
```

### Restore

```bash
# Restore ChromaDB
docker run --rm -v corpus_chroma_data:/data -v $(pwd)/backup:/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/chroma-20240101.tar.gz -C /"
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose -f .docker/docker-compose.yml logs corpus_api

# Common issues:
# - Config file not found: Ensure configs/ is mounted
# - Port already in use: Change port mapping
# - Ollama not accessible: Check host.docker.internal
```

### ChromaDB Connection Failed

```bash
# Verify ChromaDB is healthy
docker compose -f .docker/docker-compose.yml exec chroma curl localhost:8000/api/v1/heartbeat

# Check network
docker compose -f .docker/docker-compose.yml exec corpus_api ping chroma
```

### Slow Responses

1. **Model loading**: First request loads models into memory
2. **Large documents**: Increase `timeout_seconds` in config
3. **Resource limits**: Check CPU/memory with `docker stats`

### Out of Memory

```yaml
# Add memory limits to docker-compose
services:
  corpus_api:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Debug Mode

```bash
# Run API with debug logging
docker compose -f .docker/docker-compose.yml run --rm \
  -e LOG_LEVEL=DEBUG corpus_api
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CORPUS_CALLOSUM_CONFIG` | Path to config file | `configs/corpus_callosum.yaml` |
| `PYTHONPATH` | Python module path | `/app/src` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

## Quick Reference

```bash
# Start
docker compose -f .docker/docker-compose.yml up -d

# Stop
docker compose -f .docker/docker-compose.yml down

# Rebuild
docker compose -f .docker/docker-compose.yml up -d --build

# Logs
docker compose -f .docker/docker-compose.yml logs -f

# Status
docker compose -f .docker/docker-compose.yml ps

# Shell into container
docker compose -f .docker/docker-compose.yml exec corpus_api /bin/bash
```
