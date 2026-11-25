
import csv
import math
from pathlib import Path
from statistics import mean, stdev
from collections import defaultdict
from itertools import product

from config import LOADS, SPLITS, SEEDS


T_CRITICAL = 2.262157

SCOPES = ("link_1", "link_2", "aggregate")

METRICS = ("throughput_mbps", "average_delay_ms", "frame_loss_percent", "utilization_percent", "average_queue_delay_ms")

METRIC_COLUMNS = [f"{scope}_{metric}" for scope in SCOPES for metric in METRICS] + ["utilization_gap_pp", "link_1_max_queue_length", "link_2_max_queue_length"]

def load_results(filename):
    groups = defaultdict(dict)

    with open(filename, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            load = float(row["total_load_mbps"])
            split = float(row["traffic_split"])
            seed = int(row["seed"])

            key = (load, split)

            if seed in groups[key]:
                raise ValueError(f"Duplicate run: {key}, seed {seed}")

            values = {metric: float(row[metric]) for metric in METRIC_COLUMNS}

            if not all(math.isfinite(v) for v in values.values()):
                raise ValueError("Invalid metric value.")

            groups[key][seed] = values

    #verify official experimental configurations
    expected = set(product(LOADS, SPLITS))

    if set(groups) != expected:
        raise ValueError("Unexpected experimental configurations.")

    for key, runs in groups.items():
        if set(runs) != set(SEEDS):
            raise ValueError(f"Incorrect seeds for {key}")

    return groups


def calculate_statistics(values):
    n = len(values)

    if n != 10:
        raise ValueError("Expected 10 observations.")

    average = mean(values)
    standard_deviation = stdev(values)
    standard_error = standard_deviation / math.sqrt(n)

    margin_of_error = T_CRITICAL * standard_error

    return {
        "n": n,
        "mean": average,
        "standard_deviation": standard_deviation,
        "standard_error": standard_error,
        "ci_lower": average - margin_of_error,
        "ci_upper": average + margin_of_error}


def summarize_results(groups):
    results = []

    for (load, split), runs in sorted(groups.items()):
        for metric in METRIC_COLUMNS:

            values = [run[metric] for run in runs.values()]

            row = {
                "total_load_mbps": load,
                "traffic_split": split,
                "metric": metric}

            row.update(calculate_statistics(values))
            results.append(row)

    return results


def compare_baseline(groups):
    results = []

    for load in LOADS:
        baseline = groups[(load, 0.5)]

        for split in SPLITS:
            if split == 0.5:
                continue

            current = groups[(load, split)]

            for metric in METRIC_COLUMNS:

                baseline_mean = mean(run[metric] for run in baseline.values())

                current_mean = mean(run[metric] for run in current.values())

                difference = current_mean - baseline_mean

                percent_change = (difference / baseline_mean * 100 if baseline_mean != 0 else None)

                results.append({
                    "total_load_mbps": load,
                    "baseline_split": 0.5,
                    "traffic_split": split,
                    "metric": metric,
                    "baseline_mean": baseline_mean,
                    "current_mean": current_mean,
                    "difference": difference,
                    "percent_change": percent_change})

    return results


def compare_paired_runs(groups):
    results = []

    for load in LOADS:
        baseline = groups[(load, 0.5)]

        for split in SPLITS:
            if split == 0.5:
                continue

            current = groups[(load, split)]

            for metric in METRIC_COLUMNS:

                differences = [current[seed][metric] - baseline[seed][metric] for seed in SEEDS]

                row = {
                    "total_load_mbps": load,
                    "baseline_split": 0.5,
                    "traffic_split": split,
                    "metric": metric}

                row.update(calculate_statistics(differences))

                results.append(row)

    return results


def export_csv(results, filename):
    if not results:
        raise ValueError("No results to export.")

    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0].keys()))

        writer.writeheader()
        writer.writerows(results)

    print(f"Saved {len(results)} rows to {path}")


def main():
    groups = load_results("results/experimental_results.csv")

    summary = summarize_results(groups)
    baseline = compare_baseline(groups)
    paired = compare_paired_runs(groups)

    export_csv(summary, "results/statistical_summary.csv")
    export_csv(baseline, "results/baseline_comparison.csv")
    export_csv(paired,"results/paired_comparison.csv")

    print("\nStatistical analysis completed.")


if __name__ == "__main__":
    main()