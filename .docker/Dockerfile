# CorpusRAG Docker Image
# Multi-stage: base-slim → production | base-full → development/cli

# === Base slim (no ffmpeg, no build tools) ===
FROM python:3.11-slim AS base-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash --uid 1000 corpus
USER corpus
WORKDIR /home/corpus
ENV PATH="/home/corpus/.local/bin:$PATH"

# === Production (slim — server extra only, no torch) ===
FROM base-slim AS production

COPY --chown=corpus:corpus pyproject.toml ./app/
COPY --chown=corpus:corpus src/ ./app/src/
COPY --chown=corpus:corpus configs/ ./app/configs/

RUN pip install --user --no-cache-dir "./app[server]"

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

# === Base full (with ffmpeg + build tools for video/ML) ===
FROM base-slim AS base-full

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg build-essential \
    && rm -rf /var/lib/apt/lists/*
USER corpus

# === Development (full deps) ===
FROM base-full AS development

COPY --chown=corpus:corpus pyproject.toml ./app/
COPY --chown=corpus:corpus src/ ./app/src/
COPY --chown=corpus:corpus configs/ ./app/configs/
COPY --chown=corpus:corpus tests/ ./app/tests/

RUN pip install --user --no-cache-dir -e "./app[full,dev]"

CMD ["corpus-mcp-server", "--profile", "full", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000", "--no-auth"]

# === CLI (full deps) ===
FROM base-full AS cli

COPY --chown=corpus:corpus pyproject.toml ./app/
COPY --chown=corpus:corpus src/ ./app/src/
COPY --chown=corpus:corpus configs/ ./app/configs/

RUN pip install --user --no-cache-dir "./app[full]"
CMD ["bash"]

# === Default target ===
FROM production
