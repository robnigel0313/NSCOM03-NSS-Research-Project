import csv
import json
import math
from pathlib import Path


RESULTS_DIR = Path("results")

METRIC_PROPERTIES = {
    "throughput_mbps": {
        "label": "Throughput",
        "unit": "Mbps",
        "preferred": "higher"},
    "average_delay_ms": {
        "label": "Average frame delay",
        "unit": "ms",
        "preferred": "lower"},
    "frame_loss_percent": {
        "label": "Frame loss",
        "unit": "percentage points",
        "preferred": "lower"},
    "utilization_percent": {
        "label": "Link utilization",
        "unit": "percentage points",
        "preferred": "context"},
    "average_queue_delay_ms": {
        "label": "Average queueing delay",
        "unit": "ms",
        "preferred": "lower"},
    "utilization_gap_pp": {
        "label": "Utilization gap",
        "unit": "percentage points",
        "preferred": "lower"},
    "max_queue_length": {
        "label": "Maximum queue length",
        "unit": "frames",
        "preferred": "context"}}


def read_csv(filename):
    rows = []

    with open(filename, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            converted = {}

            for key, value in row.items():
                if value == "":
                    converted[key] = None
                else:
                    try:
                        converted[key] = float(value)
                    except ValueError:
                        converted[key] = value

            rows.append(converted)

    return rows


def read_data(results_dir=RESULTS_DIR):
    results_dir = Path(results_dir)

    return {
        "experiments": read_csv(results_dir / "experimental_results.csv"),
        "summary": read_csv(results_dir / "statistical_summary.csv"),
        "baseline": read_csv(results_dir / "baseline_comparison.csv"),
        "paired": read_csv(results_dir / "paired_comparison.csv")}

def identify_metric(metric):
    scope = "system"
    metric_name = metric

    for prefix in ("aggregate_", "link_1_", "link_2_"):
        if metric.startswith(prefix):
            scope = prefix.rstrip("_")
            metric_name = metric[len(prefix):]
            break

    properties = METRIC_PROPERTIES[metric_name].copy()

    #an individual link's throughput change doesnt necessarily mean better or worse performance
    if scope in ("link_1", "link_2"):
        if metric_name == "throughput_mbps":
            properties["preferred"] = "context"

    return {
        "scope": scope,
        "metric": metric_name,
        **properties}

def classify_difference(mean, ci_lower, ci_upper):
    values = (mean, ci_lower, ci_upper)

    #for unavailable or invalid stats
    if any(
        v is None or not math.isfinite(v) for v in values):
        return "unavailable"

    if ci_lower > ci_upper:
        return "invalid"

    if not ci_lower <= mean <= ci_upper:
        return "invalid"

    if mean == 0 and ci_lower == 0 and ci_upper == 0:
        return "no_observed_difference"

    if ci_lower > 0:
        return "increase"

    if ci_upper < 0:
        return "decrease"

    return "inconclusive"

def classify_impact(direction, preferred):
    if direction not in ("increase", "decrease"):
        return direction

    if preferred == "context":
        return "context_dependent"

    if preferred == "higher":
        if direction == "increase":
            return "improvement"
        else:
            return "degradation"

    if preferred == "lower":
        if direction == "decrease":
            return "improvement"
        else:
            return "degradation"

    return "unclassified"


def interpret_metric(row):
    properties = identify_metric(row["metric"])

    load = row["total_load_mbps"]
    split = row["traffic_split"]
    baseline = row["baseline_split"]

    mean = row["mean"]
    ci_lower = row["ci_lower"]
    ci_upper = row["ci_upper"]

    direction = classify_difference(mean, ci_lower, ci_upper)

    impact = classify_impact(direction, properties["preferred"])

    label = properties["label"]
    unit = properties["unit"]
    scope = properties["scope"]

    split_label = f"{split * 100:g}/{(1 - split) * 100:.0f}"
    baseline_label = (f"{baseline * 100:g}/{(1 - baseline) * 100:.0f}")

    scope_label = {
        "aggregate": "Aggregate",
        "link_1": "Link 1",
        "link_2": "Link 2",
        "system": "System"}[scope]

    context = (
        f"At {load:g} Mbps with a {split_label} "
        f"distribution, compared with {baseline_label}, "
        f"{scope_label.lower()} {label.lower()}")

    if direction == "unavailable":
        statement = (
            f"{context} could not be assessed "
            "because the required statistics are unavailable.")

    elif direction == "invalid":
        statement = (
            f"{context} could not be assessed "
            "because the confidence interval is inconsistent.")

    elif direction == "no_observed_difference":
        statement = (
            f"{context} showed no observed difference "
            "across the paired runs.")

    elif direction == "inconclusive":
        statement = (
            f"{context} had a mean difference of "
            f"{mean:+.4f} {unit}. However, the confidence "
            "interval includes zero, providing insufficient "
            "evidence to establish the direction of change.")

    else:
        change = ("increased" if direction == "increase" else "decreased")

        statement = (
            f"{context} {change} by an average of "
            f"{abs(mean):.4f} {unit}.")

        if impact == "improvement":
            statement += (
                " The confidence interval provides "
                "evidence of improvement in this metric.")

        elif impact == "degradation":
            statement += (
                " The confidence interval provides "
                "evidence of degradation in this metric.")

        elif impact == "context_dependent":
            statement += (
                " The implications of this change depend "
                "on the other performance metrics.")

    return {
        "total_load_mbps": load,
        "traffic_split": split,
        "baseline_split": baseline,
        "metric": row["metric"],
        "scope": scope,
        "label": label,
        "unit": unit,
        "mean_difference": mean,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "direction": direction,
        "impact": impact,
        "statement": statement}


def interpret_metrics(data):
    interpretations = []

    for row in data["paired"]:
        result = interpret_metric(row)
        interpretations.append(result)

    return interpretations

def group_by_configuration(rows):
    groups = {}

    for row in rows:
        key = (row["total_load_mbps"], row["traffic_split"])

        if key not in groups:
            groups[key] = {}

        groups[key][row["metric"]] = row

    return groups



def interpret_configuration(summary, comparisons):
    findings = []

    primary_metrics = ("aggregate_throughput_mbps", "aggregate_average_delay_ms", "aggregate_frame_loss_percent")

    def get_direction(metric):
        return comparisons.get(metric, {}).get("direction", "unavailable")

    def get_impact(metric):
        return comparisons.get(metric, {}).get("impact", "unavailable")

    def get_mean(metric):
        return summary.get(metric, {}).get("mean")

    def add_finding(category, statement, metrics):
        findings.append({
            "category": category,
            "statement": statement,
            "supporting_metrics": list(metrics)})

    throughput = get_direction("aggregate_throughput_mbps")
    delay = get_direction("aggregate_average_delay_ms")
    loss = get_direction("aggregate_frame_loss_percent")
    loss_mean = get_mean("aggregate_frame_loss_percent")
    impacts = [get_impact(metric) for metric in primary_metrics]
    incomplete = any(impact in ("unavailable", "invalid", "unclassified") for impact in impacts)

    #Rule 1: reduced delivery performance
    if throughput == "decrease" and loss == "increase":
        add_finding("delivery_degradation", "Aggregate throughput decreased alongside " "an increase in frame loss.",
            ("aggregate_throughput_mbps","aggregate_frame_loss_percent"))

    #Rule 2: increased latency w/o observed loss
    if delay == "increase" and loss_mean == 0:
        add_finding("latency_without_loss", "Average frame delay increased despite " "no observed frame loss.",
            ("aggregate_average_delay_ms", "aggregate_frame_loss_percent"))

    #Rule 3: increased latency w/o clear throughput degradation
    if delay == "increase" and throughput in ("inconclusive", "no_observed_difference"):
        add_finding("latency_without_throughput_degradation", "Average frame delay increased without " "clear evidence of throughput degradation.",
            ("aggregate_average_delay_ms", "aggregate_throughput_mbps"))

    #Rule 4: overall performance
    improved = "improvement" in impacts
    degraded = "degradation" in impacts

    if improved and degraded:
        add_finding("performance_tradeoff", "Some primary performance metrics improved " "while others degraded, indicating a " "performance trade-off.", primary_metrics)

    elif incomplete:
        add_finding("incomplete_assessment", "An overall performance assessment cannot " "be completed because some required " "statistics are unavailable or invalid.", primary_metrics)

    elif improved:
        add_finding("performance_improvement", "At least one primary performance metric " "improved, with no detected degradation " "in the other primary metrics.", primary_metrics)

    elif degraded:
        add_finding("performance_degradation", "At least one primary performance metric " "degraded, with no detected improvement " "in the other primary metrics.", primary_metrics)

    elif all(impact == "no_observed_difference" for impact in impacts):
        add_finding("no_observed_difference", "No differences were observed in the " "primary performance metrics across " "the paired runs.", primary_metrics)

    else:
        add_finding("inconclusive_performance_change", "The available comparisons do not establish " "a clear improvement or degradation " "in the primary performance metrics.", primary_metrics)

    #Rule 5: absolute frame loss assessment
    if loss_mean is None or not math.isfinite(loss_mean):
        add_finding("loss_unavailable", "Frame loss could not be assessed.", ("aggregate_frame_loss_percent",) )

    elif loss_mean == 0:
        add_finding("no_observed_loss", "No frame loss was observed in the " "experimental runs.", ("aggregate_frame_loss_percent",))

    elif 0 < loss_mean <= 100:
        add_finding("observed_loss", f"The mean aggregate frame loss was " f"{loss_mean:.4f}%.", ("aggregate_frame_loss_percent",))

    else:
        add_finding("invalid_loss", "The reported frame loss is outside " "its valid range.", ("aggregate_frame_loss_percent",))

    return findings


def interpret_configurations(data, interpretations):
    summary_groups = group_by_configuration(data["summary"])
    comparison_groups = group_by_configuration(interpretations)

    results = []

    for key, comparisons in sorted(comparison_groups.items()):
        load, split = key

        summary = summary_groups.get(key, {})

        findings = interpret_configuration(summary, comparisons)

        results.append({
            "total_load_mbps": load,
            "traffic_split": split,
            "baseline_split": next(iter(comparisons.values()))["baseline_split"],
            "findings": findings})

    return results


def calculate_effective_capacity(link_capacity_mbps, payload_bytes, occupancy_byte_times):
    if (link_capacity_mbps <= 0
        or payload_bytes <= 0
        or occupancy_byte_times < payload_bytes):
        raise ValueError("Invalid link configuration.")

    return (link_capacity_mbps * payload_bytes / occupancy_byte_times)


def classify_capacity(offered_load, effective_capacity):
    if (offered_load is None
        or not math.isfinite(offered_load)
        or offered_load < 0):
        return "unavailable"

    if offered_load == 0:
        return "no_traffic"

    if math.isclose(offered_load, effective_capacity, rel_tol=1e-9):
        return "at_capacity"

    if offered_load > effective_capacity:
        return "above_capacity"

    return "below_capacity"



def interpret_link_capacity(offered_load, effective_capacity, utilization, generated, dropped):
    condition = classify_capacity(offered_load, effective_capacity)

    findings = []

    if condition == "no_traffic":
        findings.append("No traffic was assigned to this link.")

    elif condition == "above_capacity":
        findings.append(f"The offered load of {offered_load:.2f} Mbps "
            f"exceeds the effective capacity of "
            f"{effective_capacity:.2f} Mbps. "
            "The link is theoretically overloaded.")

    elif condition == "at_capacity":
        findings.append("The offered load is at the theoretical " "capacity limit of the link.")

    elif condition == "below_capacity":
        findings.append("The offered load is below the effective " "capacity of the link.")

    else:
        findings.append("The capacity condition could not be assessed.")

    #interpret observed frame loss
    if generated is None or dropped is None:
        findings.append("Frame loss information is unavailable.")

    elif generated < 0 or dropped < 0 or dropped > generated:
        findings.append("The reported frame counts are invalid.")

    elif generated == 0:
        findings.append("No frames were generated, so frame loss " "performance cannot be assessed.")

    elif dropped == 0:
        findings.append("No frame loss was observed.")

    elif condition == "below_capacity":
        findings.append("Frame loss occurred despite the offered " "load being below effective capacity, " "indicating temporary buffer overflow " "within the simulation.")

    else:
        findings.append("Frame loss was observed.")

    if (utilization is not None
        and math.isfinite(utilization)
        and 0 <= utilization <= 100):
        findings.append(f"Mean link utilization was "
            f"{utilization:.2f}%.")

    return {"offered_load_mbps": offered_load,
        "effective_capacity_mbps": effective_capacity,
        "capacity_condition": condition,
        "utilization_percent": utilization,
        "generated": generated,
        "dropped": dropped,
        "findings": findings}



def interpret_bottleneck(link_1, link_2):
    condition_1 = link_1["capacity_condition"]
    condition_2 = link_2["capacity_condition"]

    conditions = (condition_1, condition_2)

    if "unavailable" in conditions:
        return {"category": "unavailable",
            "statement": ("The system capacity condition " "could not be fully assessed.")}

    if conditions == ("no_traffic", "no_traffic"):
        return {"category": "no_traffic",
            "statement": ("No traffic was assigned to either link.")}

    if conditions == ("above_capacity", "above_capacity"):
        return {"category": "both_links_overloaded",
            "statement": ("Both links receive offered traffic " "above their effective capacities.")}

    if "above_capacity" in conditions:
        overloaded = ("Link 1" if condition_1 == "above_capacity" else "Link 2")

        other = ("Link 2" if overloaded == "Link 1" else "Link 1")

        total_load = (link_1["offered_load_mbps"] + link_2["offered_load_mbps"])
        total_capacity = (link_1["effective_capacity_mbps"] + link_2["effective_capacity_mbps"])

        if total_load < total_capacity:
            return {"category": "imbalance_bottleneck",
                "statement": (f"{overloaded} is overloaded despite "
                    "the total offered load being below "
                    "the combined effective capacity. "
                    f"Available capacity on {other} "
                    "cannot be used by the overloaded "
                    "link under the fixed traffic "
                    "assignment model.")}

        return {"category": "capacity_bottleneck",
            "statement": (f"{overloaded} is overloaded, while "
                "the total offered load is at or above "
                "the combined effective capacity.")}

    if "at_capacity" in conditions:
        return {"category": "capacity_limit",
            "statement": ("At least one link is operating at " "its theoretical offered-load limit.")}

    return {"category": "no_theoretical_overload",
        "statement": ("Neither link receives offered traffic "
            "above its effective capacity. Temporary "
            "queue buildup may still occur.")}



def interpret_capacities(data, link_capacity_mbps, payload_bytes, occupancy_byte_times):
    effective_capacity = calculate_effective_capacity(link_capacity_mbps, payload_bytes, occupancy_byte_times)

    summary_groups = group_by_configuration(data["summary"])

    experiment_groups = {}

    for row in data["experiments"]:
        key = (row["total_load_mbps"], row["traffic_split"])

        experiment_groups.setdefault(key, []).append(row)

    results = []

    for key, runs in sorted(experiment_groups.items()):
        load, split = key
        summary = summary_groups.get(key, {})

        links = {}

        for scope in ("link_1", "link_2"):
            offered_load = runs[0][f"{scope}_offered_load_mbps"]

            utilization = summary.get(f"{scope}_utilization_percent", {}).get("mean")

            generated = sum(row[f"{scope}_generated"] for row in runs)

            dropped = sum(row[f"{scope}_dropped"] for row in runs)

            links[scope] = interpret_link_capacity(
                offered_load,
                effective_capacity,
                utilization,
                generated,
                dropped)

        bottleneck = interpret_bottleneck(links["link_1"], links["link_2"])

        results.append({"total_load_mbps": load,
            "traffic_split": split,
            "combined_effective_capacity_mbps": (
                effective_capacity * 2),
            **links,
            "bottleneck": bottleneck})

    return results


def configuration_label(load, split):
    return (f"{load:g} Mbps " 
            f"({split * 100:g}/{(1 - split) * 100:g})")


def collect_configurations(results, category):
    configurations = []

    for result in results:
        if any(finding["category"] == category for finding in result["findings"]):
            configurations.append(configuration_label(result["total_load_mbps"], result["traffic_split"]))

    return configurations



def interpret_overall(data, configurations, capacities):
    findings = []

    categories = {"delivery_degradation": "Reduced throughput alongside increased frame loss",
        "latency_without_loss": "Increased latency without observed frame loss",
        "latency_without_throughput_degradation": "Increased latency without clear evidence " "of throughput degradation",
        "performance_tradeoff": "Trade-offs between primary performance metrics",
        "performance_improvement": "Detected improvement without detected degradation",
        "performance_degradation": "Detected degradation without detected improvement",
        "no_observed_difference": "No observed differences in primary metrics",
        "inconclusive_performance_change": "Inconclusive changes in primary performance metrics",
        "incomplete_assessment": "Incomplete performance assessment"}

    #summarize recurring findings
    for category, description in categories.items():
        matches = collect_configurations(configurations, category)

        if matches:
            findings.append({"category": category,
                "count": len(matches),
                "configurations": matches,
                "statement": (f"{description} was identified in "
                    f"{len(matches)} configuration(s): "
                    f"{', '.join(matches)}.")})

    #summarize theoretical cap conditions
    capacity_categories = {"imbalance_bottleneck": "Imbalance-induced theoretical overload",
        "capacity_bottleneck": "Link overload with total offered load " "at or above combined effective capacity",
        "both_links_overloaded": "Theoretical overload on both links",
        "capacity_limit": "Operation at the theoretical capacity limit",
        "no_theoretical_overload": "No theoretical link overload",
        "no_traffic": "No assigned traffic",
        "unavailable": "Unavailable capacity assessment"}

    for category, description in capacity_categories.items():
        matches = [configuration_label(result["total_load_mbps"], result["traffic_split"]) for result in capacities if result["bottleneck"]["category"] == category]

        if matches:
            findings.append({"category": category,
                "count": len(matches),
                "configurations": matches,
                "statement": (f"{description} was identified in "
                    f"{len(matches)} configuration(s): "
                    f"{', '.join(matches)}.")})

    return findings



def identify_extremes(data):
    metrics = {"aggregate_throughput_mbps": {"label": "Aggregate throughput", "unit": "Mbps"},
        "aggregate_average_delay_ms": {"label": "Average frame delay", "unit": "ms"},
        "aggregate_frame_loss_percent": {"label": "Frame loss", "unit": "%"}}

    groups = {}

    for row in data["summary"]:
        metric = row["metric"]
        value = row["mean"]

        if metric not in metrics:
            continue

        if value is None or not math.isfinite(value):
            continue

        key = (row["total_load_mbps"], metric)

        groups.setdefault(key, []).append(row)

    results = []

    for (load, metric), rows in sorted(groups.items()):
        if len(rows) < 2:
            continue

        minimum = min(row["mean"] for row in rows)
        maximum = max(row["mean"] for row in rows)

        lowest = [row["traffic_split"] for row in rows if row["mean"] == minimum]
        highest = [row["traffic_split"] for row in rows if row["mean"] == maximum]

        results.append({"total_load_mbps": load,
            "metric": metric,
            "label": metrics[metric]["label"],
            "unit": metrics[metric]["unit"],
            "minimum_mean": minimum,
            "minimum_splits": lowest,
            "maximum_mean": maximum,
            "maximum_splits": highest,
            "all_equal": minimum == maximum})

    return results


def interpret_data(data, link_capacity_mbps, payload_bytes, occupancy_byte_times):
    metrics = interpret_metrics(data)

    configurations = interpret_configurations(data, metrics)
    capacities = interpret_capacities(data, link_capacity_mbps, payload_bytes, occupancy_byte_times)

    overall = interpret_overall(data, configurations, capacities)

    extremes = identify_extremes(data)

    return {"metric_interpretations": metrics,
        "configuration_findings": configurations,
        "capacity_findings": capacities,
        "overall_findings": overall,
        "performance_extremes": extremes}



def generate_overview(data, link_capacity_mbps, payload_bytes, occupancy_byte_times):
    experiments = data["experiments"]

    loads = sorted({row["total_load_mbps"] for row in experiments})

    splits = sorted({row["traffic_split"] for row in experiments})

    seeds = sorted({int(row["seed"]) for row in experiments})

    durations = sorted({row["duration_seconds"] for row in experiments})

    configurations = {(row["total_load_mbps"], row["traffic_split"]) for row in experiments}

    effective_capacity = calculate_effective_capacity(link_capacity_mbps, payload_bytes, occupancy_byte_times)

    return {"total_runs": len(experiments),
        "total_configurations": len(configurations),
        "offered_loads_mbps": loads,
        "traffic_splits": splits,
        "seeds": seeds,
        "observation_durations_seconds": durations,
        "number_of_links": 2,
        "nominal_link_capacity_mbps": link_capacity_mbps,
        "effective_link_capacity_mbps": effective_capacity,
        "combined_effective_capacity_mbps": (
            effective_capacity * 2),
        "payload_bytes": payload_bytes,
        "occupancy_byte_times": occupancy_byte_times,
        "confidence_level_percent": 95}



def generate_performance_summary(data):
    groups = group_by_configuration(data["summary"])

    results = []

    for (load, split), metrics in sorted(groups.items()):
        row = {"total_load_mbps": load,
            "traffic_split": split,
            "configuration": configuration_label(load, split)}

        for metric, statistics in metrics.items():
            row[metric] = {"mean": statistics["mean"],
                "standard_deviation": (statistics["standard_deviation"]),
                "standard_error": (statistics["standard_error"]),
                "ci_lower": statistics["ci_lower"],
                "ci_upper": statistics["ci_upper"],
                "n": int(statistics["n"])}

        results.append(row)

    return results



def generate_limitations():
    return [("The simulation models two independent "
            "Ethernet links with fixed traffic assignments."),
        ("Dynamic traffic redistribution and "
        "link aggregation hashing are not modeled."),
        ("Results apply to the simulated configurations "
        "and may not generalize to physical networks."),
        ("Confidence intervals are individual 95% "
        "intervals without adjustment for "
        "multiple comparisons."),
        ("Inconclusive comparisons do not establish "
        "equivalent performance."),
        ("Theoretical capacity limits do not establish "
        "the exact experimental onset of frame loss."),
        ("Performance extremes describe observed means "
        "and do not necessarily establish statistically "
        "supported differences.")]




def generate_report(data, link_capacity_mbps, payload_bytes, occupancy_byte_times):
    overview = generate_overview(data, link_capacity_mbps, payload_bytes, occupancy_byte_times)

    interpretations = interpret_data(data, link_capacity_mbps, payload_bytes, occupancy_byte_times)

    performance_summary = (generate_performance_summary(data))

    return {"title": ("Performance Analysis of Traffic Imbalance "
        "in Aggregated Ethernet Links Using "
        "Discrete-Event Simulation"),
        "overview": overview,
        "performance_summary": performance_summary, **interpretations,
        "limitations": generate_limitations()}


def export_json(report, filename):
    path = Path(filename)

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump( report, file, indent=2, ensure_ascii=False, allow_nan=False)

    print(f"JSON report saved to: {path}")


def main():
    data = read_data()

    report = generate_report(data, link_capacity_mbps=100, payload_bytes=1500, occupancy_byte_times=1538)

    export_json(report, RESULTS_DIR / "report.json")

    print("\nReport generation completed.")


if __name__ == "__main__":
    main()