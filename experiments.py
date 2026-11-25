
import csv
import time
from pathlib import Path
from itertools import product

from config import LOADS, SPLITS, SEEDS, DEFAULTS
from simulation import run_simulation
from metrics import calculate_metrics


def run_experiments(loads=LOADS, splits=SPLITS, seeds=SEEDS, settings=None):
    if settings is None:
        settings = DEFAULTS.copy()

    results = []

    configurations = list(product(loads, splits, seeds))
    total_runs = len(configurations)

    start_time = time.perf_counter()

    for run_number, (load, split, seed) in enumerate(configurations, start=1):
        print(
            f"[{run_number}/{total_runs}] "
            f"Load: {load} Mbps | "
            f"Split: {split * 100:.0f}/"
            f"{(1 - split) * 100:.0f} | "
            f"Seed: {seed}",
            flush=True)

        #execute simulation without storing individual frame records and periodic queue sampling to reduce memory usage and speed up execution
        raw = run_simulation(total_load_mbps=load, traffic_split=split, seed=seed, record_limit=0, queue_sample_interval=None, **settings)

        #performance metrics
        metrics = calculate_metrics(raw)

        #store experimental parameters
        row = {
            "total_load_mbps": load,
            "traffic_split": split,
            "seed": seed,
            "duration_seconds": raw["observation_duration"],
            "link_1_offered_load_mbps": raw["link_1"]["offered_load_mbps"],
            "link_2_offered_load_mbps": raw["link_2"]["offered_load_mbps"]}

        #store per-link and aggregate results
        for scope in ("link_1", "link_2", "aggregate"):
            source = raw if scope == "aggregate" else raw[scope]

            for name, value in source["counts"].items():
                row[f"{scope}_{name}"] = value

            for name, value in metrics[scope].items():
                row[f"{scope}_{name}"] = value

        #additional indicators for collecting supplementary measurements to help explain the effects of uneven traffic distribution
        row["utilization_gap_pp"] = abs(metrics["link_1"]["utilization_percent"] - metrics["link_2"]["utilization_percent"])
        row["link_1_max_queue_length"] = (raw["link_1"]["max_queue_length"])
        row["link_2_max_queue_length"] = (raw["link_2"]["max_queue_length"])

        results.append(row)

    elapsed = time.perf_counter() - start_time

    print(f"\nCompleted {total_runs} simulation runs.")
    print(f"Execution time: {elapsed:.2f} seconds")

    return results


def export_results(results, filename):
    if not results:
        raise ValueError("No experimental results to export.")

    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0].keys()))

        writer.writeheader()
        writer.writerows(results)

    print(f"Results saved to: {path}")


def main():

    results = run_experiments()

    export_results(results, "results/experimental_results.csv")


if __name__ == "__main__":
    main()
