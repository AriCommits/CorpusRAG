# src/homeschool/generate_compose_env.py
# Called by setup.py — users never run this manually

from src.homeschool.config import load
from pathlib import Path

cfg = load()

env_lines = [
    f"CHROMA_TOKEN={cfg.chromadb.auth_token}",
    f"CHROMA_BIND={cfg.network.bind_host}:{cfg.network.ports['chromadb']}",
    f"VAULT_PATH={cfg.paths.vault}",
    f"MODEL_STORE={cfg.paths.model_store}",
    f"LLAMA_CUBLAS={'1' if cfg.hardware.is_nvidia else '0'}",
]

out = Path(__file__).parent.parent / ".compose.env"
out.write_text("\n".join(env_lines))
print(f"[✓] Generated {out}")