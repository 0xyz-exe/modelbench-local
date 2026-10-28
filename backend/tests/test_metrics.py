import pytest
from backend.app.benchmark.metrics import compute_statistics, aggregate_iteration_metrics

def test_compute_statistics_empty():
    stats = compute_statistics([])
    assert stats["mean"] == 0.0
    assert stats["median"] == 0.0
    assert stats["p95"] == 0.0

def test_compute_statistics_values():
    vals = [10.0, 20.0, 30.0, 40.0, 50.0]
    stats = compute_statistics(vals)
    assert stats["mean"] == 30.0
    assert stats["median"] == 30.0
    assert stats["min"] == 10.0
    assert stats["max"] == 50.0
    assert stats["p90"] >= 40.0

def test_aggregate_iteration_metrics():
    iterations = [
        {"status": "success", "tokens_per_sec": 30.0, "ttft_ms": 100.0, "latency_ms": 500.0},
        {"status": "success", "tokens_per_sec": 40.0, "ttft_ms": 120.0, "latency_ms": 450.0},
        {"status": "failed", "tokens_per_sec": 0.0, "ttft_ms": 0.0, "latency_ms": 1000.0},
    ]
    quality = [1.0, 0.8]
    agg = aggregate_iteration_metrics(iterations, quality)
    assert agg["successful_iterations"] == 2
    assert agg["failed_iterations"] == 1
    assert round(agg["error_rate"], 2) == 0.33
    assert agg["tps"]["mean"] == 35.0
    assert agg["average_quality_score"] == 0.9
