"""Shared MCP tool telemetry wrapper."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


def log_tool(
    store,
    name: str,
    fn: Callable[[], Any],
    *,
    input_size: int = 0,
) -> Any:
    """Run ``fn`` and record duration/success on ``store`` when present."""
    start = time.perf_counter()
    result = fn()
    if store:
        success = True
        if isinstance(result, dict):
            success = result.get("status") != "error"
        store.log(
            name,
            (time.perf_counter() - start) * 1000,
            input_size=input_size,
            success=success,
        )
    return result
