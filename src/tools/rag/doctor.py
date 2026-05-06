"""Health check diagnostics for CorpusRAG."""

import httpx


def run_doctor(config) -> list[tuple[bool, str]]:
    """Run all health checks. Returns list of (passed, message)."""
    results = []

    results.append((True, "Config loaded: configs/base.yaml"))

    # ChromaDB
    host, port = config.database.host, config.database.port
    try:
        r = httpx.get(f"http://{host}:{port}/api/v2/heartbeat", timeout=5)
        if r.status_code == 200:
            from db import ChromaDBBackend

            db = ChromaDBBackend(config.database)
            cols = db.list_collections()
            results.append((True, f"ChromaDB reachable: {host}:{port} ({len(cols)} collections)"))
        else:
            results.append((False, f"ChromaDB unhealthy: {host}:{port} (status {r.status_code})"))
    except Exception as e:
        results.append((False, f"ChromaDB unreachable: {host}:{port} - {e}"))

    # Ollama
    endpoint = config.llm.endpoint
    try:
        r = httpx.get(f"{endpoint}/api/tags", timeout=5)
        if r.status_code == 200:
            results.append((True, f"Ollama reachable: {endpoint}"))
            models = [m["name"] for m in r.json().get("models", [])]
            model_names = [m.split(":")[0] for m in models]

            # LLM model
            llm_model = config.llm.model.split(":")[0]
            if llm_model in model_names:
                results.append((True, f"LLM model available: {config.llm.model}"))
            else:
                results.append((False, f"LLM model NOT found: {config.llm.model} (available: {', '.join(models)})"))

            # Embedding model
            embed_model = config.embedding.model.split(":")[0]
            if embed_model in model_names:
                results.append((True, f"Embedding model available: {config.embedding.model}"))
            else:
                results.append((False, f"Embedding model NOT found: {config.embedding.model} (available: {', '.join(models)})"))

            # Test embedding
            try:
                er = httpx.post(
                    f"{endpoint}/api/embed",
                    json={"model": config.embedding.model, "input": "test"},
                    timeout=30,
                )
                if er.status_code == 200:
                    dims = len(er.json().get("embeddings", [[]])[0])
                    results.append((True, f"Test embedding: {dims} dimensions"))
                else:
                    results.append((False, f"Embedding failed: status {er.status_code}"))
            except Exception as e:
                results.append((False, f"Embedding failed: {e}"))
        else:
            results.append((False, f"Ollama unhealthy: {endpoint}"))
    except Exception as e:
        results.append((False, f"Ollama unreachable: {endpoint} - {e}"))

    return results
