import argparse
import os

import matplotlib.pyplot as plt

from .metrics import load_metrics, aggregate_per_second
from .analysis import compare_run_to_baseline


def main():
    parser = argparse.ArgumentParser(description="Plot throughput over time for a run.")
    parser.add_argument("--run-id", required=True, help="Run ID to plot (directory under runs/).")
    parser.add_argument(
        "--baseline-id",
        required=False,
        help="Optional baseline run ID (used to overlay anomaly windows).",
    )
    parser.add_argument(
        "--filename",
        default="metrics.csv",
        help="Metrics filename inside runs/<run-id>/ (e.g., metrics.csv or redis_metrics.csv).",
    )
    args = parser.parse_args()

    # Load and aggregate metrics
    df = load_metrics(args.run_id, filename=args.filename)
    agg = aggregate_per_second(df)

    # Use relative seconds from start of the run for the x-axis
    min_ts = agg["ts_sec"].min()
    agg["rel_sec"] = agg["ts_sec"] - min_ts

    # Create the plot
    plt.figure()
    plt.plot(agg["rel_sec"], agg["throughput_rps"], label="Throughput (req/s)")
    plt.xlabel("Time (s)")
    plt.ylabel("Throughput (req/s)")
    plt.title(f"Throughput over time for run '{args.run_id}'")

    # Overlay anomaly windows from comparison
    if args.baseline_id:
        comparison = compare_run_to_baseline(args.baseline_id, args.run_id)
        windows = comparison.get("anomaly_windows", [])
        first = True
        for w in windows:
            start = w["start_sec"]
            end = w["end_sec"]

            label = "Anomaly window" if first else None
            plt.axvspan(start, end, alpha=0.2, color="#8FB1CC", label=label)
            first = False

        if windows:
            plt.legend()

    out_dir = os.path.join("runs", args.run_id)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "throughput.png")
    plt.tight_layout()
    plt.savefig(out_path)
    print(f"Saved throughput plot to {out_path}")

        # If we have a baseline, also create a comparison bar chart
    if args.baseline_id:
        comparison = compare_run_to_baseline(args.baseline_id, args.run_id)

        base = comparison["baseline_summary"]
        run = comparison["run_summary"]

        # Metrics to compare
        metric_keys = ["throughput_rps", "p95_latency_ms", "error_rate"]
        metric_labels = ["Throughput (req/s)", "p95 latency (ms)", "Error rate"]

        baseline_vals = [base[k] for k in metric_keys]
        run_vals = [run[k] for k in metric_keys]

        x = list(range(len(metric_keys)))
        width = 0.35

        plt.figure()
        plt.title(f"Baseline vs run comparison ('{args.baseline_id}' vs '{args.run_id}')")
        plt.xticks(x, metric_labels, rotation=15)
        plt.ylabel("Value")

        # Baseline bars
        baseline_positions = [i - width / 2 for i in x]
        run_positions = [i + width / 2 for i in x]

        plt.bar(baseline_positions, baseline_vals, width, label="Baseline")
        plt.bar(run_positions, run_vals, width, label="Run")

        plt.legend()
        plt.tight_layout()

        comp_path = os.path.join(out_dir, "comparison.png")
        plt.savefig(comp_path)
        print(f"Saved comparison plot to {comp_path}")

if __name__ == "__main__":
    main()
