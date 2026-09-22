"""Subprocess checks for fast, dependency-light CLI help startup."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
BANNED_MODULES = (
    "chromadb",
    "textual",
    "torch",
    "faster_whisper",
    "sentence_transformers",
    "transformers",
)


@pytest.mark.parametrize(
    ("args", "expected_commands"),
    [
        (["--help"], ("tools",)),
        (["tools", "--help"], ("video", "rag")),
        (["tools", "video", "--help"], ("video", "transcribe")),
        (["tools", "rag", "--help"], ("rag", "ingest")),
    ],
)
def test_help_does_not_load_heavy_modules(
    args: list[str], expected_commands: tuple[str, ...]
) -> None:
    """Each help path stays lightweight in a fresh Python process.

    The parent pytest process can already have imported optional dependencies,
    so invoking Click through a subprocess is essential.  We deliberately do
    not impose a wall-clock target: the intended local target is sub-second,
    but CI timing is inherently noisy.
    """
    script = """
import json
import sys
from click.testing import CliRunner
from cli import corpus

args = json.loads(sys.argv[1])
expected = json.loads(sys.argv[2])
result = CliRunner().invoke(corpus, args)
banned = json.loads(sys.argv[3])
payload = {
    "exit": result.exit_code,
    "leaked": [name for name in banned if name in sys.modules],
    "output_ok": all(name in result.output for name in expected),
}
print(json.dumps(payload))
"""
    environment = os.environ.copy()
    source_path = str(REPO_ROOT / "src")
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (source_path, environment.get("PYTHONPATH")))
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            json.dumps(args),
            json.dumps(expected_commands),
            json.dumps(BANNED_MODULES),
        ],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["exit"] == 0
    assert payload["leaked"] == []
    assert payload["output_ok"] is True
