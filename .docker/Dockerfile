# sync_worker/Dockerfile
FROM python:3.12-slim-bookworm

# Only what's needed for llama-cpp-python compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cmake \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Build llama-cpp-python with CUDA if available, fall back to CPU
ARG LLAMA_CUBLAS=0
RUN if [ "$LLAMA_CUBLAS" = "1" ]; then \
    CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --no-cache-dir; \
    else \
    pip install llama-cpp-python --no-cache-dir; \
    fi

RUN pip install --no-cache-dir -r requirements.txt

COPY sync.py .

CMD ["python", "sync.py"]
```
