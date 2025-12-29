import argparse
import json
from typing import Dict, Any, List
from .config import load_config
from .metrics import load_metrics, aggregate_per_second, compute_summary_stats


def detect_anomalies(
    base_summary: Dict[str, Any],
    run_agg,
    throughput_drop_threshold: float | None = None,
    error_rate_threshold: float | None = None,
    warmup_ignore_sec: float | None = None,
) -> Dict[str, Any]:
    """
    Detect anomaly windows and approximate recovery time.

    - A second is "anomalous" if:
      * throughput_rps < baseline_throughput * (1 - throughput_drop_threshold)
        (e.g. more than 50% drop), OR
      * error_rate > error_rate_threshold

    We assume run_agg has columns: ts_sec, throughput_rps, error_rate.
    """
    config = load_config()
    anom_cfg = config.get("anomaly_detection", {})

    throughput_drop_threshold = (
        throughput_drop_threshold
        if throughput_drop_threshold is not None
        else anom_cfg.get("throughput_drop_threshold", 0.5)
    )

    error_rate_threshold = (
        error_rate_threshold
        if error_rate_threshold is not None
        else anom_cfg.get("error_rate_threshold", 0.1)
    )

    warmup_ignore_sec = (
        warmup_ignore_sec
        if warmup_ignore_sec is not None
        else anom_cfg.get("warmup_ignore_sec", 2)
    )

    baseline_tp = base_summary.get("throughput_rps") or 0.0
    if baseline_tp <= 0 or run_agg.empty:
        return {"anomaly_windows": [], "recovery_time_sec": None}

    # Normalize time so min ts_sec = 0 for this run
    min_ts = run_agg["ts_sec"].min()
    run_agg = run_agg.copy()
    run_agg["rel_sec"] = run_agg["ts_sec"] - min_ts 

    # Ignore first N seconds as warmup to avoid tiny startup blips
    run_agg = run_agg[run_agg["rel_sec"] >= warmup_ignore_sec]
    if run_agg.empty:
        return {"anomaly_windows": [], "recovery_time_sec": None}

    # Conditions for anomaly
    tp_threshold = baseline_tp * (1.0 - throughput_drop_threshold)

    def is_anomalous(row) -> bool:
        tp = row["throughput_rps"]
        err = row["error_rate"]
        if tp < tp_threshold:
            return True
        if err is not None and err > error_rate_threshold:
            return True
        return False

    run_agg["is_anomaly"] = run_agg.apply(is_anomalous, axis=1)

    # Build contiguous anomaly windows
    anomaly_rows = run_agg[run_agg["is_anomaly"]]
    if anomaly_rows.empty:
        return {"anomaly_windows": [], "recovery_time_sec": None}

    anomaly_windows: List[Dict[str, Any]] = []
    current_start = None
    prev_t = None

    for _, row in anomaly_rows.sort_values("rel_sec").iterrows():
        t = int(row["rel_sec"])
        if current_start is None:
            # start new window
            current_start = t
            prev_t = t
        elif t == prev_t + 1:
            # continue current window
            prev_t = t
        else:
            # gap -> close previous window
            anomaly_windows.append({"start_sec": current_start, "end_sec": prev_t})
            current_start = t
            prev_t = t

    # close last window
    if current_start is not None:
        anomaly_windows.append({"start_sec": current_start, "end_sec": prev_t})

    # Define recovery time as: last anomalous second - first anomalous second
    first_start = anomaly_windows[0]["start_sec"]
    last_end = anomaly_windows[-1]["end_sec"]
    recovery_time_sec = last_end - first_start

    return {
        "anomaly_windows": anomaly_windows,
        "recovery_time_sec": float(recovery_time_sec),
    }


def compare_run_to_baseline(baseline_id: str, run_id: str) -> Dict[str, Any]:
    base_df = load_metrics(baseline_id)
    run_df = load_metrics(run_id)

    base_agg = aggregate_per_second(base_df)
    run_agg = aggregate_per_second(run_df)

    base_summary = compute_summary_stats(base_agg)
    run_summary = compute_summary_stats(run_agg)

    base_tp = base_summary["throughput_rps"] or 0.0
    run_tp = run_summary["throughput_rps"] or 0.0

    throughput_drop_pct = 0.0
    if base_tp > 0:
        throughput_drop_pct = (base_tp - run_tp) / base_tp * 100.0

    anomaly_info = detect_anomalies(base_summary, run_agg)

    result: Dict[str, Any] = {
        "baseline_id": baseline_id,
        "run_id": run_id,
        "baseline_summary": base_summary,
        "run_summary": run_summary,
        "throughput_drop_pct": throughput_drop_pct,
        "anomaly_windows": anomaly_info["anomaly_windows"],
        "recovery_time_sec": anomaly_info["recovery_time_sec"],
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Compare a run to a baseline.")
    parser.add_argument("--baseline-id", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    result = compare_run_to_baseline(args.baseline_id, args.run_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
