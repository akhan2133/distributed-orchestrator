import pandas as pd
from pathlib import Path
from typing import Dict, Any


def load_metrics(run_id: str, filename: str = "metrics.csv") -> pd.DataFrame:
    path = Path("runs") / run_id / filename
    if not path.exists():
        raise FileNotFoundError(f"Metrics file not found for run_id={run_id}: {path}")

    df = pd.read_csv(path)
    df["timestamp"] = df["timestamp"].astype(float)
    df["latency_ms"] = df["latency_ms"].astype(float)
    return df


def aggregate_per_second(df: pd.DataFrame) -> pd.DataFrame:
    df["ts_sec"] = df["timestamp"].astype(int)

    grouped = df.groupby("ts_sec").agg(
        requests=("timestamp", "count"),
        avg_latency_ms=("latency_ms", "mean"),
        error_count=("error", lambda s: (s.notna() & (s != "")).sum()),
    )

    grouped["error_rate"] = grouped["error_count"] / grouped["requests"].clip(lower=1)
    grouped["throughput_rps"] = grouped["requests"]

    return grouped.reset_index()


def compute_summary_stats(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {
            "throughput_rps": 0.0,
            "p50_latency_ms": None,
            "p95_latency_ms": None,
            "error_rate": None,
        }

    throughput = df["throughput_rps"].mean()
    p50_latency = df["avg_latency_ms"].quantile(0.5)
    p95_latency = df["avg_latency_ms"].quantile(0.95)
    error_rate = df["error_rate"].mean()

    return {
        "throughput_rps": float(throughput),
        "p50_latency_ms": float(p50_latency),
        "p95_latency_ms": float(p95_latency),
        "error_rate": float(error_rate),
    }
