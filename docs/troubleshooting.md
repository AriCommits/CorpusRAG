# CorpusCallosum Troubleshooting Guide

This guide helps diagnose and resolve common issues with CorpusCallosum.

## 🔍 Quick Diagnostic Steps

### 1. Check Service Status

```bash
# Docker deployment
docker compose ps

# Local installation
corpus-mcp-server --help
```

### 2. Review Logs

```bash
# Docker logs
docker compose logs -f corpus-mcp
docker compose logs -f chromadb

# Local logs (check systemd or application logs)
journalctl -u corpus-callosum -f
```

### 3. Test Connectivity

```bash
# MCP Server health
curl http://localhost:8000/health

# ChromaDB health  
curl http://localhost:8001/api/v1/heartbeat

# Ollama health
curl http://localhost:11434/api/tags
```

## 🚨 Common Issues

### MCP Server Issues

#### **Issue: MCP Server Won't Start**

**Symptoms:**
- Container exits immediately
- "Connection refused" errors
- Health check failures

**Diagnosis:**
```bash
# Check container logs
docker compose logs corpus-mcp

# Check configuration
docker compose exec corpus-mcp python -c "from corpus_callosum.config import load_config; print(load_config())"
```

**Solutions:**
1. **Port conflict:**
   ```bash
   # Check what's using port 8000
   netstat -tlnp | grep :8000
   
   # Use different port
   CC_MCP_PORT=8080 docker compose up
   ```

2. **Configuration errors:**
   ```bash
   # Validate configuration
   docker compose exec corpus-mcp corpus-db list
   ```

3. **Database connection issues:**
   ```bash
   # Test ChromaDB connection
   docker compose exec corpus-mcp python -c "import chromadb; print(chromadb.HttpClient(host='chromadb', port=8000).list_collections())"
   ```

#### **Issue: MCP Tools Not Working**

**Symptoms:**
- "Tool not found" errors
- Empty tool responses
- MCP connection timeouts

**Solutions:**
1. **Verify tool registration:**
   ```bash
   # List available tools
   curl http://localhost:8000/mcp/tools
   ```

2. **Check tool configuration:**
   ```bash
   # Test specific tool
   curl -X POST http://localhost:8000/mcp/tools/rag_query \
     -H "Content-Type: application/json" \
     -d '{"collection": "test", "query": "hello"}'
   ```

### Database Issues

#### **Issue: ChromaDB Connection Failed**

**Symptoms:**
- "Connection refused to ChromaDB"
- Database health check failures
- Collections not accessible

**Diagnosis:**
```bash
# Check ChromaDB status
docker compose ps chromadb

# Test direct connection
curl -v http://localhost:8001/api/v1/heartbeat
```

**Solutions:**
1. **Service dependency issues:**
   ```bash
   # Restart with proper order
   docker compose down
   docker compose up chromadb
   sleep 30
   docker compose up corpus-mcp
   ```

2. **Volume permission issues:**
   ```bash
   # Fix ChromaDB data permissions
   docker compose exec chromadb chown -R 1000:1000 /chroma
   ```

3. **Network connectivity:**
   ```bash
   # Test internal network
   docker compose exec corpus-mcp ping chromadb
   ```

#### **Issue: Collections Missing or Corrupted**

**Symptoms:**
- Empty collection lists
- "Collection not found" errors
- Unexpected search results

**Solutions:**
1. **List and verify collections:**
   ```bash
   docker compose exec corpus-mcp corpus-db list
   ```

2. **Backup and restore:**
   ```bash
   # Create backup
   docker compose exec corpus-mcp corpus-db backup-all --output-dir /data/emergency_backup
   
   # Restore specific collection
   docker compose exec corpus-mcp corpus-db restore /data/backups/collection.tar.gz
   ```

3. **Rebuild collections:**
   ```bash
   # Re-ingest documents
   docker compose exec corpus-mcp corpus-rag ingest --path /data/vault --collection rebuilt_collection
   ```

### LLM Integration Issues

#### **Issue: Ollama Connection Failed**

**Symptoms:**
- LLM generation timeouts
- "Model not found" errors
- Empty or error responses

**Diagnosis:**
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Test model availability
curl http://localhost:11434/api/show -d '{"name": "llama3"}'
```

**Solutions:**
1. **Pull missing models:**
   ```bash
   docker compose exec ollama ollama pull llama3
   docker compose exec ollama ollama pull nomic-embed-text
   ```

2. **Increase timeouts:**
   ```bash
   # Set longer timeout
   CC_LLM_TIMEOUT_SECONDS=300 docker compose up corpus-mcp
   ```

3. **Check Ollama logs:**
   ```bash
   docker compose logs ollama
   ```

#### **Issue: Poor LLM Response Quality**

**Symptoms:**
- Nonsensical responses
- Incomplete generations
- Wrong format outputs

**Solutions:**
1. **Adjust temperature:**
   ```yaml
   # In configuration
   llm:
     temperature: 0.3  # More deterministic
   ```

2. **Use different models:**
   ```bash
   # Try different model
   CC_LLM_MODEL=mistral docker compose up corpus-mcp
   ```

3. **Check prompt templates:**
   ```python
   # Validate prompts in development
   from corpus_callosum.llm.prompts import PromptTemplates
   templates = PromptTemplates()
   print(templates.flashcard_generation_prompt("test content", 5, "intermediate", "math"))
   ```

### Performance Issues

#### **Issue: Slow Response Times**

**Symptoms:**
- Long wait times for operations
- Timeout errors
- High CPU/memory usage

**Diagnosis:**
```bash
# Check resource usage
docker stats

# Monitor specific services
docker compose top
```

**Solutions:**
1. **Increase resources:**
   ```yaml
   # In docker-compose.yml
   services:
     corpus-mcp:
       deploy:
         resources:
           limits:
             memory: 4G
             cpus: '2.0'
   ```

2. **Optimize batch sizes:**
   ```bash
   # Use smaller chunks for ingestion
   corpus-rag ingest --path /data --collection test --chunk-size 500
   ```

3. **Use local models:**
   ```yaml
   # Switch to faster embedding model
   embedding:
     backend: sentence-transformers
     model: all-MiniLM-L6-v2
   ```

#### **Issue: High Memory Usage**

**Solutions:**
1. **Limit model memory:**
   ```bash
   # Set Ollama memory limits
   OLLAMA_MAX_LOADED_MODELS=1 docker compose up ollama
   ```

2. **Clean up unused collections:**
   ```bash
   # Remove old collections
   docker compose exec corpus-mcp corpus-db list
   docker compose exec corpus-mcp python -c "
   from corpus_callosum.db import ChromaDBBackend
   from corpus_callosum.config import load_config
   db = ChromaDBBackend(load_config().database)
   db.delete_collection('old_collection_name')
   "
   ```

### Configuration Issues

#### **Issue: Configuration Not Loading**

**Symptoms:**
- Default values used instead of custom config
- "Configuration file not found" errors
- Environment variables ignored

**Solutions:**
1. **Check config file path:**
   ```bash
   # Verify mounted configuration
   docker compose exec corpus-mcp ls -la /home/corpus/app/configs/
   ```

2. **Validate YAML syntax:**
   ```bash
   # Test config loading
   docker compose exec corpus-mcp python -c "
   from corpus_callosum.config import load_config
   config = load_config('/home/corpus/app/configs/base.yaml')
   print(config)
   "
   ```

3. **Environment variable precedence:**
   ```bash
   # Check environment
   docker compose exec corpus-mcp env | grep CC_
   ```

### Network and Connectivity Issues

#### **Issue: Service Discovery Problems**

**Symptoms:**
- Services can't reach each other
- "Host not found" errors
- Intermittent connectivity

**Solutions:**
1. **Check Docker network:**
   ```bash
   # List networks
   docker network ls
   
   # Inspect network
   docker network inspect corpuscallosum_corpus-network
   ```

2. **Test inter-service connectivity:**
   ```bash
   # Test from MCP server to ChromaDB
   docker compose exec corpus-mcp ping chromadb
   docker compose exec corpus-mcp curl http://chromadb:8000/api/v1/heartbeat
   ```

3. **DNS resolution:**
   ```bash
   # Check service names resolve
   docker compose exec corpus-mcp nslookup chromadb
   ```

## 🔧 Advanced Debugging

### Enable Debug Logging

```yaml
# In docker-compose.yml or environment
environment:
  - CC_LOG_LEVEL=DEBUG
  - CC_DEVELOPMENT=true
```

### Access Container Shell

```bash
# Get interactive shell
docker compose exec corpus-mcp bash

# For debugging
docker compose exec corpus-mcp python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from corpus_callosum.mcp_server.server import create_mcp_server
server = create_mcp_server()
print('Server created successfully')
"
```

### Memory and Resource Monitoring

```bash
# Monitor resource usage
while true; do
  echo "=== $(date) ==="
  docker stats --no-stream
  sleep 30
done
```

### Database Debugging

```bash
# Direct ChromaDB interaction
docker compose exec corpus-mcp python -c "
import chromadb
client = chromadb.HttpClient(host='chromadb', port=8000)
print('Collections:', client.list_collections())
"

# Check collection details
docker compose exec corpus-mcp python -c "
import chromadb
client = chromadb.HttpClient(host='chromadb', port=8000)
collection = client.get_collection('your_collection_name')
print('Count:', collection.count())
print('Sample:', collection.peek())
"
```

## 📋 Diagnostic Data Collection

When reporting issues, collect this information:

```bash
#!/bin/bash
# diagnostic_info.sh

echo "=== System Information ==="
uname -a
docker --version
docker compose version

echo "=== Docker Compose Status ==="
docker compose ps

echo "=== Service Logs (last 100 lines) ==="
docker compose logs --tail=100 corpus-mcp
docker compose logs --tail=100 chromadb

echo "=== Health Checks ==="
curl -s http://localhost:8000/health || echo "MCP server unreachable"
curl -s http://localhost:8001/api/v1/heartbeat || echo "ChromaDB unreachable"

echo "=== Resource Usage ==="
docker stats --no-stream

echo "=== Network Configuration ==="
docker network inspect corpuscallosum_corpus-network

echo "=== Volume Information ==="
docker volume ls | grep corpus
```

## 📞 Getting Help

1. **Check the logs first** - Most issues show clear error messages
2. **Search existing issues** in the GitHub repository
3. **Provide diagnostic information** when reporting issues
4. **Use minimal reproduction cases** when possible

## 🔄 Reset Procedures

### Soft Reset (Keep Data)
```bash
docker compose down
docker compose up -d
```

### Hard Reset (Lose Data)
```bash
docker compose down -v
docker compose up -d
```

### Nuclear Option (Complete Cleanup)
```bash
docker compose down -v --rmi all
docker system prune -a
```

⚠️ **Warning:** Hard reset and nuclear option will destroy all data and require re-downloading models.