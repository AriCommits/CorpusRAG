from utils.benchmarking import RAGBenchmarker


def test_benchmarker_records_time():
    benchmarker = RAGBenchmarker()

    # Record a simulated 100ms retrieval, 200ms generation, 300ms total
    benchmarker.record(0.1, 0.2, 0.3)

    assert len(benchmarker.history) == 1
    assert benchmarker.history[0].retrieval_ms == 100.0
    assert benchmarker.history[0].generation_ms == 200.0
    assert benchmarker.history[0].total_ms == 300.0

    stats = benchmarker.get_stats()
    assert stats["avg_total_ms"] == 300.0
    assert stats["count"] == 1.0


def test_benchmarker_p95():
    benchmarker = RAGBenchmarker()
    # Record 10 measurements: 10, 20, ..., 100
    for i in range(1, 11):
        benchmarker.record(0, 0, i * 0.01)

    stats = benchmarker.get_stats()
    # p95 of [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    # index = int(10 * 0.95) = 9
    # totals[9] = 100
    assert stats["p95_total_ms"] == 100.0
    assert stats["avg_total_ms"] == 55.0
