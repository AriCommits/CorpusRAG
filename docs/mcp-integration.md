# CorpusRAG MCP Integration Guide

This guide covers how to integrate CorpusRAG with AI agents through the Model Context Protocol (MCP), enabling programmatic access to all learning and knowledge management functionality.

## Overview

CorpusRAG provides a comprehensive MCP server that exposes all CLI tools as callable functions, along with database resources and workflow prompts. This enables AI agents to:

- Ingest and query documents
- Generate study materials (flashcards, summaries, quizzes)
- Process videos and transcripts
- Access collection information
- Execute pre-built learning workflows

## MCP Server Architecture

The CorpusRAG MCP server is built using **FastMCP** (FastAPI-based MCP implementation) and provides:

- **Tools**: All CorpusRAG functionality exposed as callable functions
- **Resources**: Database state and collection information
- **Prompts**: Pre-built workflow templates for common learning tasks
- **Health Endpoints**: Container orchestration and monitoring support

### Server Components

```
┌─────────────────────────────────────────────────────┐
│                MCP Server                           │
├─────────────────────────────────────────────────────┤
│  Tools Layer                                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │  RAG Tools  │ │Content Gen  │ │Video Tools  │   │
│  │ • ingest    │ │• flashcards │ │• transcribe │   │
│  │ • query     │ │• summaries  │ │• clean      │   │
│  │ • retrieve  │ │• quizzes    │ │             │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
├─────────────────────────────────────────────────────┤
│  Resources Layer                                    │
│  ┌─────────────┐ ┌─────────────┐                   │
│  │Collections  │ │Collection   │                   │
│  │List         │ │Info         │                   │
│  └─────────────┘ └─────────────┘                   │
├─────────────────────────────────────────────────────┤
│  Prompts Layer                                      │
│  ┌─────────────┐ ┌─────────────┐                   │
│  │Study Session│ │Lecture      │                   │
│  │Template     │ │Processing   │                   │
│  └─────────────┘ └─────────────┘                   │
└─────────────────────────────────────────────────────┘
```

## Editor Configuration

Configure your editor or AI agent to connect to CorpusRAG via MCP using the `corpus-mcp-server` entry point.

### Claude Desktop

```json
{
  "mcpServers": {
    "corpusrag": {
      "command": "corpus-mcp-server",
      "args": ["--profile", "dev", "--transport", "stdio"]
    }
  }
}
```

### Kiro CLI

```json
{
  "mcpServers": {
    "corpusrag": {
      "command": "corpus-mcp-server",
      "args": ["--profile", "dev", "--transport", "stdio"]
    }
  }
}
```

### Neovim (codecompanion.nvim)

```lua
require("codecompanion").setup({
  adapters = {
    mcp = {
      name = "corpusrag",
      cmd = "corpus-mcp-server",
      args = { "--profile", "dev", "--transport", "stdio" },
    },
  },
})
```

### OpenCode

```json
{
  "mcpServers": {
    "corpusrag": {
      "command": "corpus-mcp-server",
      "args": ["--profile", "dev", "--transport", "stdio"]
    }
  }
}
```

## Starting the MCP Server

### Basic Usage

```bash
# Start with stdio for editor integration (default)
corpus-mcp-server --profile dev

# Start with HTTP transport
corpus-mcp-server --profile full --transport streamable-http --port 8000

# Custom configuration and port
corpus-mcp-server --config production.yaml --port 9000

# Bind to specific host
corpus-mcp-server --host localhost --port 8080
```

### Command Line Options

- `--profile` - Tool profile to expose: `dev`, `learn`, or `full` (default: `full`)
- `--transport` - Transport type: `stdio` or `streamable-http` (default: `stdio`)
- `--config, -c` - Configuration file path (optional, defaults to `configs/base.yaml`)
- `--host` - Host to bind to (default: `0.0.0.0`, HTTP transport only)
- `--port` - Port to bind to (default: `8000`, HTTP transport only)
- `--no-auth` - Disable authentication for local development (HTTP transport only)

### Docker Deployment

```yaml
services:
  corpus-mcp:
    image: corpus-callosum:latest
    ports:
      - "8000:8000"
    environment:
      - CORPUSRAG_DATABASE_HOST=chromadb
      - CORPUSRAG_LLM_ENDPOINT=http://ollama:11434
    depends_on:
      - chromadb
      - ollama
```

### Health Monitoring

The MCP server provides health endpoints for monitoring:

- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check with database connectivity

**Health Response Example:**
```json
{
  "status": "healthy",
  "service": "corpus-callosum-mcp",
  "version": "0.6.0",
  "timestamp": "2026-04-07"
}
```

**Readiness Response Example:**
```json
{
  "status": "ready",
  "database": "connected",
  "collections": 5
}
```

## MCP Tools

All CorpusRAG functionality is exposed as MCP tools with standardized JSON interfaces.

### RAG Tools

#### `rag_ingest`
Ingest documents into a RAG collection.

**Parameters:**
```json
{
  "path": "string (required) - Path to file or directory",
  "collection": "string (required) - Collection name",
  "chunk_size": "integer (optional, default: 1000) - Size of text chunks",
  "chunk_overlap": "integer (optional, default: 200) - Overlap between chunks"
}
```

**Response:**
```json
{
  "status": "success",
  "collection": "research_papers",
  "documents_processed": 15,
  "chunks_created": 247
}
```

**Usage Example:**
```python
result = await client.call_tool("rag_ingest", {
    "path": "./documents",
    "collection": "course_materials",
    "chunk_size": 500,
    "chunk_overlap": 50
})
```

#### `rag_query`
Query a RAG collection and generate a response.

**Parameters:**
```json
{
  "collection": "string (required) - Collection name",
  "query": "string (required) - Question or query text",
  "top_k": "integer (optional, default: 5) - Number of chunks to retrieve"
}
```

**Response:**
```json
{
  "status": "success",
  "query": "What is machine learning?",
  "response": "Machine learning is a subset of artificial intelligence..."
}
```

**Usage Example:**
```python
result = await client.call_tool("rag_query", {
    "collection": "ai_textbook",
    "query": "Explain neural networks",
    "top_k": 8
})
```

#### `rag_retrieve`
Retrieve relevant chunks without generating a response.

**Parameters:**
```json
{
  "collection": "string (required) - Collection name",
  "query": "string (required) - Search query text",
  "top_k": "integer (optional, default: 5) - Number of chunks to retrieve"
}
```

**Response:**
```json
{
  "status": "success",
  "query": "photosynthesis",
  "chunks": [
    {
      "text": "Photosynthesis is the process by which...",
      "source": "biology_textbook.pdf",
      "score": 0.89
    }
  ]
}
```

### Content Generation Tools

#### `generate_flashcards`
Generate flashcards from a collection.

**Parameters:**
```json
{
  "collection": "string (required) - Collection name",
  "count": "integer (optional, default: 10) - Number of flashcards",
  "difficulty": "string (optional, default: 'medium') - easy/medium/hard",
  "output_format": "string (optional, default: 'plain') - plain/anki/quizlet"
}
```

**Response:**
```json
{
  "status": "success",
  "collection": "biology_notes",
  "count": 15,
  "flashcards": [
    "What is photosynthesis?\tThe process by which plants convert light energy...",
    "Define enzyme specificity\tThe characteristic of enzymes to catalyze..."
  ]
}
```

#### `generate_summary`
Generate a summary from a collection.

**Parameters:**
```json
{
  "collection": "string (required) - Collection name",
  "topic": "string (optional) - Specific topic to focus on",
  "length": "string (optional, default: 'medium') - short/medium/long",
  "include_keywords": "boolean (optional, default: true) - Include key terms",
  "include_outline": "boolean (optional, default: false) - Include outline"
}
```

**Response:**
```json
{
  "status": "success",
  "collection": "chemistry_lectures",
  "topic": "organic chemistry",
  "summary": "# Organic Chemistry Summary\n\n## Key Concepts..."
}
```

#### `generate_quiz`
Generate a quiz from a collection.

**Parameters:**
```json
{
  "collection": "string (required) - Collection name",
  "count": "integer (optional, default: 10) - Number of questions",
  "question_types": "array[string] (optional) - Types of questions",
  "output_format": "string (optional, default: 'markdown') - markdown/json/csv"
}
```

**Response:**
```json
{
  "status": "success",
  "collection": "physics_notes",
  "count": 10,
  "quiz": "# Physics Quiz\n\n## Question 1..."
}
```

### Video Processing Tools

#### `transcribe_video`
Transcribe a video file using Whisper.

**Parameters:**
```json
{
  "video_path": "string (required) - Path to video file",
  "collection": "string (required) - Collection to store transcript",
  "model": "string (optional, default: 'base') - Whisper model size"
}
```

**Response:**
```json
{
  "status": "success",
  "video_path": "./lecture01.mp4",
  "collection": "course_transcripts",
  "transcript": "Welcome to today's lecture on quantum mechanics..."
}
```

#### `clean_transcript`
Clean and format a transcript using LLM.

**Parameters:**
```json
{
  "transcript_text": "string (required) - Raw transcript to clean",
  "model": "string (optional) - LLM model for cleaning"
}
```

**Response:**
```json
{
  "status": "success",
  "cleaned_transcript": "# Lecture: Quantum Mechanics\n\nWelcome to today's discussion..."
}
```

## MCP Resources

Resources provide access to database state and collection information.

### Collections List
**URI:** `collections://list`

Returns a newline-separated list of all collections:

```
- biology_notes
- chemistry_flashcards
- physics_lectures
- research_papers
```

### Collection Information
**URI:** `collection://{collection_name}`

Returns information about a specific collection:

```
Collection: biology_notes
Document count: 145
```

**Usage Example:**
```python
# List all collections
collections = await client.read_resource("collections://list")

# Get specific collection info
info = await client.read_resource("collection://biology_notes")
```

## MCP Prompts

Pre-built prompts for common learning workflows.

### Study Session Prompt
**Name:** `study_session_prompt`

**Parameters:**
- `collection` - Collection name
- `topic` - Topic to study

**Generated Prompt:**
```
Please help me study the topic "photosynthesis" from the collection "biology_notes".

I would like you to:
1. Provide a clear summary of the main concepts
2. Generate flashcards for key terms and concepts
3. Create a quiz to test my understanding

Use the following tools in sequence:
- generate_summary(collection="biology_notes", topic="photosynthesis")
- generate_flashcards(collection="biology_notes", count=15)
- generate_quiz(collection="biology_notes", count=10)
```

### Lecture Processing Prompt
**Name:** `lecture_processing_prompt`

**Parameters:**
- `video_path` - Path to lecture video
- `course` - Course identifier

**Generated Prompt:**
```
Please process the lecture video at "./lecture05.mp4" for course "BIO101".

Steps:
1. Transcribe the video using transcribe_video()
2. Clean the transcript using clean_transcript()
3. Ingest the transcript into a RAG collection
4. Generate study materials (summary, flashcards, quiz)

This will create a comprehensive study resource from the lecture.
```

## Agent Integration Patterns

### Basic Query Pattern

```python
import asyncio
from mcp.client import ClientSession, stdio_client

async def query_knowledge_base():
    """Basic pattern for querying a knowledge base."""
    async with stdio_client() as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()
            
            # Query the knowledge base
            result = await session.call_tool("rag_query", {
                "collection": "course_materials",
                "query": "What are the key concepts in machine learning?",
                "top_k": 5
            })
            
            print(result["response"])

asyncio.run(query_knowledge_base())
```

### Study Session Workflow

```python
async def create_study_session(collection: str, topic: str):
    """Complete study session creation workflow."""
    async with stdio_client() as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Generate summary
            summary = await session.call_tool("generate_summary", {
                "collection": collection,
                "topic": topic,
                "length": "medium",
                "include_keywords": True
            })
            
            # Generate flashcards
            flashcards = await session.call_tool("generate_flashcards", {
                "collection": collection,
                "count": 20,
                "difficulty": "medium",
                "output_format": "anki"
            })
            
            # Generate quiz
            quiz = await session.call_tool("generate_quiz", {
                "collection": collection,
                "count": 15,
                "output_format": "markdown"
            })
            
            return {
                "summary": summary["summary"],
                "flashcards": flashcards["flashcards"],
                "quiz": quiz["quiz"]
            }

# Usage
materials = await create_study_session("biology_notes", "cellular_respiration")
```

### Document Processing Pipeline

```python
async def process_documents(document_path: str, collection: str):
    """Process documents into searchable knowledge base."""
    async with stdio_client() as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Ingest documents
            ingest_result = await session.call_tool("rag_ingest", {
                "path": document_path,
                "collection": collection,
                "chunk_size": 500,
                "chunk_overlap": 50
            })
            
            # Verify collection was created
            collections = await session.read_resource("collections://list")
            
            # Generate initial study materials
            summary = await session.call_tool("generate_summary", {
                "collection": collection,
                "length": "long",
                "include_keywords": True,
                "include_outline": True
            })
            
            return {
                "ingestion": ingest_result,
                "collections": collections,
                "summary": summary["summary"]
            }
```

### Video Lecture Processing

```python
async def process_lecture_video(video_path: str, course: str, lecture_num: int):
    """Process lecture video into complete study materials."""
    collection = f"{course}_lecture_{lecture_num:02d}"
    
    async with stdio_client() as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Transcribe video
            transcript_result = await session.call_tool("transcribe_video", {
                "video_path": video_path,
                "collection": collection,
                "model": "medium"
            })
            
            # Clean transcript
            cleaned_result = await session.call_tool("clean_transcript", {
                "transcript_text": transcript_result["transcript"]
            })
            
            # Generate study materials from transcript
            materials = await create_study_session(collection, f"Lecture {lecture_num}")
            
            return {
                "transcript": cleaned_result["cleaned_transcript"],
                "study_materials": materials
            }
```

### Multi-Collection Research

```python
async def research_across_collections(query: str, collections: list[str]):
    """Research a topic across multiple collections."""
    async with stdio_client() as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            results = {}
            
            # Query each collection
            for collection in collections:
                try:
                    result = await session.call_tool("rag_query", {
                        "collection": collection,
                        "query": query,
                        "top_k": 3
                    })
                    results[collection] = result["response"]
                except Exception as e:
                    results[collection] = f"Error: {str(e)}"
            
            # Synthesize results
            synthesis_query = f"""
            Based on these responses from different sources:
            
            {chr(10).join([f"From {col}: {resp}" for col, resp in results.items()])}
            
            Please provide a comprehensive synthesis of the information about: {query}
            """
            
            # Use the first collection for synthesis
            if collections:
                synthesis = await session.call_tool("rag_query", {
                    "collection": collections[0],
                    "query": synthesis_query,
                    "top_k": 1
                })
                results["synthesis"] = synthesis["response"]
            
            return results
```

## Configuration for MCP

### Server Configuration

The MCP server uses the same configuration system as CLI tools:

```yaml
# configs/mcp-server.yaml
llm:
  endpoint: http://localhost:11434
  model: llama3
  timeout_seconds: 180.0  # Longer timeout for complex operations

database:
  mode: http              # Use HTTP for multi-user access
  host: chromadb
  port: 8000

embedding:
  backend: ollama
  model: nomic-embed-text

# Tool-specific optimizations
rag:
  chunking:
    size: 1000            # Larger chunks for better context
    overlap: 100
  retrieval:
    top_k_final: 8        # More results for comprehensive answers

flashcards:
  cards_per_topic: 15
  max_context_chars: 15000

video:
  transcription:
    model: medium         # Better accuracy for lectures
```

### Environment Variables for Docker

```bash
# LLM Configuration
CORPUSRAG_LLM_ENDPOINT=http://ollama:11434
CORPUSRAG_LLM_MODEL=llama3

# Database Configuration  
CORPUSRAG_DATABASE_MODE=http
CORPUSRAG_DATABASE_HOST=chromadb
CORPUSRAG_DATABASE_PORT=8000

# Performance tuning
CORPUSRAG_RAG_CHUNKING_SIZE=1000
CORPUSRAG_RAG_RETRIEVAL_TOP_K_FINAL=8
```

### Client Configuration

For MCP clients, configure connection settings:

```python
# MCP client configuration
mcp_config = {
    "server_url": "http://localhost:8000",
    "timeout": 300,  # 5 minutes for complex operations
    "retry_attempts": 3
}
```

## Error Handling

### Common Error Patterns

**Collection Not Found:**
```json
{
  "error": "Collection 'unknown_collection' not found",
  "error_code": "COLLECTION_NOT_FOUND"
}
```

**Invalid Parameters:**
```json
{
  "error": "Invalid difficulty level 'extreme'. Must be one of: easy, medium, hard",
  "error_code": "INVALID_PARAMETER"
}
```

**Database Connection Error:**
```json
{
  "error": "Failed to connect to ChromaDB at localhost:8000",
  "error_code": "DATABASE_CONNECTION_ERROR"
}
```

### Error Handling in Agents

```python
async def safe_tool_call(session, tool_name, params):
    """Safe tool calling with error handling."""
    try:
        result = await session.call_tool(tool_name, params)
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "tool": tool_name,
            "params": params
        }

# Usage
result = await safe_tool_call(session, "rag_query", {
    "collection": "might_not_exist",
    "query": "test query"
})

if result["status"] == "error":
    print(f"Tool call failed: {result['error']}")
else:
    print(f"Success: {result}")
```

## Performance Optimization

### Concurrent Operations

```python
import asyncio

async def parallel_collection_queries(session, collections, query):
    """Query multiple collections in parallel."""
    tasks = []
    
    for collection in collections:
        task = session.call_tool("rag_query", {
            "collection": collection,
            "query": query,
            "top_k": 5
        })
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    processed = {}
    for collection, result in zip(collections, results):
        if isinstance(result, Exception):
            processed[collection] = {"error": str(result)}
        else:
            processed[collection] = result
    
    return processed
```

### Batch Processing

```python
async def batch_flashcard_generation(session, collections):
    """Generate flashcards for multiple collections."""
    batch_size = 3  # Limit concurrent operations
    
    for i in range(0, len(collections), batch_size):
        batch = collections[i:i + batch_size]
        
        tasks = [
            session.call_tool("generate_flashcards", {
                "collection": col,
                "count": 10,
                "difficulty": "medium"
            })
            for col in batch
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Process batch results
        for collection, result in zip(batch, results):
            print(f"Generated {result['count']} flashcards for {collection}")
            
        # Brief pause between batches
        await asyncio.sleep(1)
```

### Resource Management

```python
async def efficient_study_session(session, collection, topic):
    """Optimized study session with resource management."""
    
    # First, check if collection exists
    collections = await session.read_resource("collections://list")
    if collection not in collections:
        return {"error": f"Collection {collection} not found"}
    
    # Get collection info to estimate processing time
    info = await session.read_resource(f"collection://{collection}")
    
    # Adjust parameters based on collection size
    doc_count = int(info.split("Document count: ")[1])
    
    if doc_count < 50:
        chunk_size = 500
        top_k = 3
    elif doc_count < 200:
        chunk_size = 750
        top_k = 5
    else:
        chunk_size = 1000
        top_k = 8
    
    # Generate materials with optimized settings
    summary = await session.call_tool("generate_summary", {
        "collection": collection,
        "topic": topic,
        "length": "medium"
    })
    
    flashcards = await session.call_tool("generate_flashcards", {
        "collection": collection,
        "count": min(15, doc_count // 3)  # Scale with content
    })
    
    return {
        "summary": summary["summary"],
        "flashcards": flashcards["flashcards"]
    }
```

## Security Considerations

### Input Validation

```python
def validate_collection_name(name: str) -> bool:
    """Validate collection name for security."""
    import re
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', name)) and len(name) <= 50

def validate_file_path(path: str) -> bool:
    """Validate file path to prevent directory traversal."""
    import os
    return not ('..' in path or path.startswith('/') or ':' in path)
```

### Rate Limiting

```python
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_calls: int = 100, time_window: int = 3600):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = defaultdict(list)
    
    def check_rate_limit(self, client_id: str) -> bool:
        now = time.time()
        calls = self.calls[client_id]
        
        # Remove old calls
        calls[:] = [call_time for call_time in calls if now - call_time < self.time_window]
        
        if len(calls) >= self.max_calls:
            return False
        
        calls.append(now)
        return True
```

### Access Control

```python
async def authorized_tool_call(session, tool_name, params, api_key: str):
    """Tool call with API key validation."""
    if not validate_api_key(api_key):
        return {"error": "Invalid API key", "status": "unauthorized"}
    
    return await session.call_tool(tool_name, params)

def validate_api_key(key: str) -> bool:
    """Validate API key against allowed keys."""
    # Implement your API key validation logic
    return key in get_valid_api_keys()
```

This comprehensive MCP integration guide provides everything needed to integrate CorpusRAG with AI agents, from basic setup to advanced patterns and security considerations.