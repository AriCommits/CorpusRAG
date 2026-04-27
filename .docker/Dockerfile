# CorpusRAG Docker Image
# Multi-stage build: base → production (default) | development | cli

# =============================================================================
# Stage 1: Base
# =============================================================================
FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git poppler-utils ffmpeg build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash --uid 1000 corpus
USER corpus
WORKDIR /home/corpus
ENV PATH="/home/corpus/.local/bin:$PATH"

# =============================================================================
# Stage 2: Production
# =============================================================================
FROM base AS production

COPY --chown=corpus:corpus pyproject.toml ./app/
COPY --chown=corpus:corpus src/ ./app/src/
COPY --chown=corpus:corpus configs/ ./app/configs/

RUN pip install --user --no-cache-dir ./app

RUN mkdir -p ./data/chroma_store ./data/vault ./data/scratch ./data/output

COPY --chown=corpus:corpus .docker/healthcheck.py ./healthcheck.py

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python ./healthcheck.py || exit 1

EXPOSE 8000

ENV CORPUSRAG_DATABASE_PERSIST_DIRECTORY=/home/corpus/data/chroma_store \
    CORPUSRAG_PATHS_VAULT=/home/corpus/data/vault \
    CORPUSRAG_PATHS_SCRATCH_DIR=/home/corpus/data/scratch \
    CORPUSRAG_PATHS_OUTPUT_DIR=/home/corpus/data/output

CMD ["corpus-mcp-server", "--profile", "full", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000", "--no-auth"]

# =============================================================================
# Stage 3: Development
# =============================================================================
FROM base AS development

COPY --chown=corpus:corpus pyproject.toml ./app/
COPY --chown=corpus:corpus src/ ./app/src/
COPY --chown=corpus:corpus configs/ ./app/configs/
COPY --chown=corpus:corpus tests/ ./app/tests/

RUN pip install --user --no-cache-dir -e "./app[full,dev]"

CMD ["corpus-mcp-server", "--profile", "full", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000", "--no-auth"]

# =============================================================================
# Stage 4: CLI
# =============================================================================
FROM production AS cli
CMD ["bash"]

# =============================================================================
# Default target
# =============================================================================
FROM production
