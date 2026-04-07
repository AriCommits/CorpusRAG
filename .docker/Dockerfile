# CorpusCallosum - Unified Docker Image
# Multi-stage build for production-ready deployment

# =============================================================================
# Stage 1: Base Python environment with system dependencies
# =============================================================================
FROM python:3.11-slim as base

# Install system dependencies for document processing and video transcription
RUN apt-get update && apt-get install -y \
    # Core system tools
    curl \
    git \
    # Document processing dependencies
    poppler-utils \
    # Video transcription dependencies  
    ffmpeg \
    # Build tools for Python packages
    build-essential \
    # Clean up to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 corpus
USER corpus
WORKDIR /home/corpus

# Set up Python environment
ENV PYTHONPATH=/home/corpus/app
ENV PATH="/home/corpus/.local/bin:$PATH"

# =============================================================================
# Stage 2: Development environment (for local development)
# =============================================================================
FROM base as development

# Copy requirements and install dependencies
COPY --chown=corpus:corpus requirements.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt

# Install development dependencies
RUN pip install --user --no-cache-dir \
    pytest>=8.0.0 \
    pytest-cov>=4.1.0 \
    ruff>=0.4.0 \
    mypy>=1.10.0 \
    types-PyYAML>=6.0.0

# Copy source code
COPY --chown=corpus:corpus . ./app/

# Install package in development mode
RUN pip install --user -e ./app

# Default command for development
CMD ["python", "-m", "corpus_callosum.mcp_server.server"]

# =============================================================================
# Stage 3: Production environment (optimized)
# =============================================================================
FROM base as production

# Copy requirements and install production dependencies only
COPY --chown=corpus:corpus requirements.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy source code
COPY --chown=corpus:corpus src/ ./app/src/
COPY --chown=corpus:corpus pyproject.toml ./app/
COPY --chown=corpus:corpus configs/ ./app/configs/

# Install package
RUN pip install --user ./app

# Create directories for data persistence
RUN mkdir -p ./data/chroma_store ./data/vault ./data/scratch ./data/output

# Health check script
COPY --chown=corpus:corpus .docker/healthcheck.py ./
RUN chmod +x ./healthcheck.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python ./healthcheck.py || exit 1

# Expose MCP server port
EXPOSE 8000

# Default configuration
ENV CC_DATABASE_PERSIST_DIRECTORY=/home/corpus/data/chroma_store
ENV CC_PATHS_VAULT=/home/corpus/data/vault
ENV CC_PATHS_SCRATCH_DIR=/home/corpus/data/scratch
ENV CC_PATHS_OUTPUT_DIR=/home/corpus/data/output

# Default command
CMD ["corpus-mcp-server", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Stage 4: CLI tools (lightweight image for CLI usage)
# =============================================================================
FROM production as cli

# Override default command for CLI usage
CMD ["bash"]

# Add helpful aliases
RUN echo 'alias cc-flashcards="corpus-flashcards"' >> ~/.bashrc && \
    echo 'alias cc-summaries="corpus-summaries"' >> ~/.bashrc && \
    echo 'alias cc-quizzes="corpus-quizzes"' >> ~/.bashrc && \
    echo 'alias cc-rag="corpus-rag"' >> ~/.bashrc && \
    echo 'alias cc-video="corpus-video"' >> ~/.bashrc && \
    echo 'alias cc-orchestrate="corpus-orchestrate"' >> ~/.bashrc

# =============================================================================
# Default target is production
# =============================================================================
FROM production