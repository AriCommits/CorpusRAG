from dataclasses import dataclass
from typing import Dict, List


@dataclass
class BenchmarkResult:
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    total_ms: float = 0.0


class RAGBenchmarker:
    """Utility to measure and record RAG performance metrics."""

    def __init__(self):
        self.history: List[BenchmarkResult] = []

    def record(self, retrieval: float, generation: float, total: float):
        """Record a set of measurements."""
        result = BenchmarkResult(
            retrieval_ms=retrieval * 1000,
            generation_ms=generation * 1000,
            total_ms=total * 1000,
        )
        self.history.append(result)
        return result

    def get_stats(self) -> Dict[str, float]:
        """Calculate average and p95 latencies."""
        if not self.history:
            return {}

        totals = sorted([r.total_ms for r in self.history])
        p95_idx = int(len(totals) * 0.95)

        return {
            "avg_total_ms": sum(totals) / len(totals),
            "p95_total_ms": totals[p95_idx],
            "count": float(len(self.history)),
        }


# Global instance for easy access
benchmarker = RAGBenchmarker()
