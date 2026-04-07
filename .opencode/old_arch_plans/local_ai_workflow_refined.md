# Refined Local AI Workflow

## Overview
This document describes a privacy-focused, local-first developer workflow for the Homeschool project. The workflow has been refined to improve usability, reliability, and alignment with the manual sync approach.

## Workflow Layers

### Layer 1: The Brain (Inference)
- **Tool:** Jan AI
- **Role:** Hosts GGUF models and provides API
- **Local API Config:** IP: `127.0.0.1` | Port: `1337`
- **Recommended Models:** Qwen 3.5 8B (general) or Qwen 2.5 Coder 7B (code-focused)
- **Manual Control:** Start/stop Jan AI as needed for resource management

### Layer 2: The Workshop (IDE)
- **Tool:** VS Code + Continue Extension
- **Role:** Primary development interface replacing Void
- **Usage:** 
  - `Cmd/Ctrl + L` for chat interactions
  - `Cmd/Ctrl + I` for inline code generation
- **Jan Connection:** Configure in VS Code Continue settings:
  ```json
  {
    "models": [{
      "title": "Jan Local",
      "provider": "openai",
      "model": "qwen3.5-8b",
      "apiBase": "http://127.0.0.1:1337/v1"
    }]
  }
  ```

### Layer 3: The Memory (RAG)
- **Tool:** ChromaDB (via Docker container)
- **Role:** Provides vector storage and retrieval for context
- **Configuration:** Managed through docker-compose in `.docker/` directory
- **Access:** Available at http://127.0.0.1:8000 when containers are running

## Workflow Operation

### Starting the Workflow
1. **Start Jan AI:** Launch Jan AI application and load desired model
2. **Start Homeschool Services:** 
   ```bash
   # From project root
   cd .docker
   docker compose up -d chromadb
   ```
3. **Develop:** Use VS Code + Continue for coding tasks with local AI assistance
4. **Process Notes:** When ready to sync:
   ```bash
   # From project root
   python -m homeschool sync
   ```

### Stopping/Cleaning Up
1. **Stop Services:**
   ```bash
   cd .docker
   docker compose down
   ```
2. **Close Applications:** Jan AI, VS Code as needed

## Configuration & Customization

### Model Management
- Store GGUF models in directory specified by `paths.model_store` in config.yaml
- Use Jan AI to manage model loading/unloading
- Switch models based on task requirements (coding vs. general reasoning)

### Resource Management
- **Memory:** Monitor model resource usage in Jan AI
- **GPU:** Configure GPU acceleration in Jan AI if available
- **Containers:** Docker resources managed through compose profiles

### Privacy Features
- All processing remains local by default
- No data leaves your machine unless explicitly configured
- ChromaDB data persists only in local volumes
- Optional: Encrypt sensitive model data at rest

## Integration Points

### With Learning Workflow
- Shared Jan AI inference engine for generating educational content
- ChromaDB stores processed notes for context-aware generation
- Manual sync trigger (`python -m homeschool sync`) serves both workflows

### With Development Tasks
- Continue extension provides AI-assisted coding
- Local models help with documentation, debugging, and code generation
- Vector search can be used for code snippet retrieval

## Troubleshooting

### Common Issues
- **Jan API not reachable:** Verify Jan AI is running and model is loaded
- **Docker issues:** Ensure Docker Desktop is running and user has permissions
- **Model loading failures:** Check GGUF file compatibility and available RAM
- **ChromaDB connection:** Verify container health with `docker ps`

### Performance Optimization
- Use model quantization for lower memory usage
- Adjust GPU layers in config.yaml based on hardware
- Monitor container logs for bottlenecks
- Consider model switching for different task types

## Best Practices

1. **Resource Awareness:** Monitor memory usage when running large models
2. **Selective Loading:** Only load models needed for current tasks
3. **Regular Updates:** Keep Jan AI, VS Code, and extensions updated
4. **Backup Configs:** Regularly export Jan AI configurations and model lists
5. **Manual Control:** Embrace the manual nature for better resource management
6. **Privacy First:** Assume all processing is local unless explicitly networked

## Advantages of This Approach

- **Privacy:** No data leaves your machine without explicit consent
- **Control:** Manual start/stop prevents unnecessary resource consumption
- **Cost:** No API usage fees; runs entirely on local hardware
- **Reliability:** Works offline and is immune to service outages
- **Flexibility:** Easy to switch models and adjust configurations
- **Learning Curve:** Builds understanding of local AI infrastructure