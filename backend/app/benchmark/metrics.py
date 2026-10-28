import math
from typing import List, Dict, Any

def compute_statistics(values: List[float]) -> Dict[str, float]:
    if not values:
        return {
            "mean": 0.0,
            "median": 0.0,
            "min": 0.0,
            "max": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "std_dev": 0.0,
        }

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mean_val = sum(sorted_vals) / n

    # Median (50th percentile)
    if n % 2 == 1:
        median_val = sorted_vals[n // 2]
    else:
        median_val = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]

    # Percentile helper
    def get_percentile(p: float) -> float:
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_vals[int(k)]
        d0 = sorted_vals[int(f)] * (c - k)
        d1 = sorted_vals[int(c)] * (k - f)
        return d0 + d1

    p90_val = get_percentile(0.90)
    p95_val = get_percentile(0.95)

    # Standard deviation
    variance = sum((x - mean_val) ** 2 for x in sorted_vals) / n if n > 0 else 0.0
    std_dev = math.sqrt(variance)

    return {
        "mean": round(mean_val, 2),
        "median": round(median_val, 2),
        "min": round(min_val, 2),
        "max": round(max_val, 2),
        "p90": round(p90_val, 2),
        "p95": round(p95_val, 2),
        "std_dev": round(std_dev, 2),
    }

def aggregate_iteration_metrics(iterations: List[Dict[str, Any]], quality_scores: List[float]) -> Dict[str, Any]:
    total = len(iterations)
    if total == 0:
        return {
            "successful_iterations": 0,
            "failed_iterations": 0,
            "error_rate": 0.0,
            "tps": compute_statistics([]),
            "ttft": compute_statistics([]),
            "latency": compute_statistics([]),
            "average_quality_score": 0.0,
        }

    successes = [it for it in iterations if it.get("status") == "success"]
    failed_count = total - len(successes)
    error_rate = round(failed_count / total, 4)

    tps_vals = [float(it["tokens_per_sec"]) for it in successes if it.get("tokens_per_sec") is not None]
    ttft_vals = [float(it["ttft_ms"]) for it in successes if it.get("ttft_ms") is not None]
    lat_vals = [float(it["latency_ms"]) for it in successes if it.get("latency_ms") is not None]

    avg_qual = round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0.0

    return {
        "successful_iterations": len(successes),
        "failed_iterations": failed_count,
        "error_rate": error_rate,
        "tps": compute_statistics(tps_vals),
        "ttft": compute_statistics(ttft_vals),
        "latency": compute_statistics(lat_vals),
        "average_quality_score": avg_qual,
    }
