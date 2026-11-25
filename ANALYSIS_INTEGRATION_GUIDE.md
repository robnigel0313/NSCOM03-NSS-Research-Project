# Analysis and Report Integration Guide

This guide describes how to integrate the performance metrics, experimental runs, statistical analysis, and automated report generation modules with the GUI.

## 1. Module Overview

| Module | Purpose |
|---|---|
| `config.py` | Defines experimental configurations and default simulation parameters. |
| `metrics.py` | Calculates individual link and aggregate performance metrics. |
| `experiments.py` | Executes batch simulations and exports experimental results. |
| `statistical_analysis.py` | Calculates descriptive statistics, confidence intervals, and baseline comparisons. |
| `report_generator.py` | Interprets experimental results and generates a structured JSON report. |
| `test_metrics.py` | Tests performance metric calculations. |
| `test_report_generator.py` | Tests statistical and network performance interpretations. |

## 2. Performance Metrics

For individual simulations, the GUI can directly import the simulation engine and metrics module.

```python
from simulation import run_simulation
from metrics import calculate_metrics

result = run_simulation(
    total_load_mbps=120,
    traffic_split=0.7,
    seed=1
)

metrics = calculate_metrics(result)
```

The returned metrics dictionary contains three scopes:

- `metrics["link_1"]`
- `metrics["link_2"]`
- `metrics["aggregate"]`

Each scope contains the following metrics:

| Key | Description | Unit |
|---|---|---|
| `throughput_mbps` | Payload throughput | Mbps |
| `average_delay_ms` | Average frame delay | ms |
| `frame_loss_percent` | Percentage of generated frames dropped | % |
| `utilization_percent` | Link utilization | % |
| `average_queue_delay_ms` | Average queueing delay | ms |

Example of accessing individual values:

```python
throughput = metrics["aggregate"]["throughput_mbps"]
delay = metrics["link_1"]["average_delay_ms"]
loss = metrics["link_2"]["frame_loss_percent"]
```

Undefined metrics may return `None`. The GUI should display these as N/A rather than zero.

## 3. Experimental Runs

The experimental module executes simulations across the configurations defined in `config.py`.

The current experimental design consists of:

- Offered loads: 80, 120, and 160 Mbps
- Traffic distributions: 50/50, 70/30, and 90/10
- Random seeds: 1–10
- Observation duration: 60 seconds
- Total configurations: 9
- Total simulation runs: 90

To execute the experiments:

```bash
python experiments.py
```

Output:

```text
results/experimental_results.csv
```

Each row represents one simulation run, containing its configuration, seed, frame counts, individual link metrics, aggregate metrics, utilization gap, and maximum queue lengths.

The existing experimental results can be loaded directly without rerunning the simulations.

## 4. Statistical Analysis

To generate statistical summaries and comparisons:

```bash
python statistical_analysis.py
```

This module produces three CSV files.

### 4.1. Statistical Summary

File: `results/statistical_summary.csv`

Contains descriptive statistics for each metric under each experimental configuration.

| Column | Description |
|---|---|
| `total_load_mbps` | Total offered load |
| `traffic_split` | Proportion assigned to Link 1 |
| `metric` | Metric identifier |
| `n` | Number of observations |
| `mean` | Mean across runs |
| `standard_deviation` | Sample standard deviation |
| `standard_error` | Standard error of the mean |
| `ci_lower` | Lower 95% confidence interval bound |
| `ci_upper` | Upper 95% confidence interval bound |

Recommended use: performance graphs, error bars, and statistical tables.

### 4.2. Baseline Comparison

File: `results/baseline_comparison.csv`

Compares each imbalanced configuration against the 50/50 baseline at the same total offered load.

Columns:

- `total_load_mbps`
- `baseline_split`
- `traffic_split`
- `metric`
- `baseline_mean`
- `current_mean`
- `difference`
- `percent_change`

The difference is calculated as the current mean minus the baseline mean.

Percentage change is undefined when the baseline mean is zero.

Recommended use: baseline comparison tables and relative performance changes.

### 4.3. Paired Comparison

File: `results/paired_comparison.csv`

Contains statistics calculated from differences between simulation runs with matching random seeds.

Columns:

- `total_load_mbps`
- `baseline_split`
- `traffic_split`
- `metric`
- `n`
- `mean`
- `standard_deviation`
- `standard_error`
- `ci_lower`
- `ci_upper`

The mean represents the average paired difference relative to the baseline.

Recommended use: confidence interval plots and statistical comparisons.

## 5. Automated Report Generation

The report generator reads the experimental and statistical CSV files, interprets the results using predefined rules, and produces structured findings.

To generate the report:

```bash
python report_generator.py
```

Output:

```text
results/report.json
```

The report can also be generated directly within Python:

```python
from report_generator import read_data, generate_report

data = read_data()

report = generate_report(
    data,
    link_capacity_mbps=100,
    payload_bytes=1500,
    occupancy_byte_times=1538
)
```

Alternatively, the GUI can load the existing JSON report:

```python
import json

with open("results/report.json", encoding="utf-8") as file:
    report = json.load(file)
```

Loading the existing report is recommended when displaying the completed research experiments.

### 5.1. Report Structure

| Key | Contents |
|---|---|
| `title` | Research project title |
| `overview` | Experimental configurations and simulation parameters |
| `performance_summary` | Statistical summaries grouped by configuration |
| `metric_interpretations` | Individual statistical comparisons and interpretations |
| `configuration_findings` | Combined performance findings for imbalanced configurations |
| `capacity_findings` | Individual link capacity conditions and system bottlenecks |
| `overall_findings` | Consolidated findings across configurations |
| `performance_extremes` | Highest and lowest observed metric means |
| `limitations` | Limitations of the simulation and analysis |

### 5.2. Accessing Overall Findings

```python
for finding in report["overall_findings"]:
    print(finding["statement"])
```

Each overall finding contains:

- `category`
- `count`
- `configurations`
- `statement`

The statement can be displayed directly in the GUI.

### 5.3. Accessing Configuration Findings

```python
for configuration in report["configuration_findings"]:
    load = configuration["total_load_mbps"]
    split = configuration["traffic_split"]

    for finding in configuration["findings"]:
        print(finding["statement"])
```

Each finding contains a category, a generated statement, and supporting metric identifiers.

### 5.4. Accessing Individual Metric Interpretations

```python
for result in report["metric_interpretations"]:
    print(result["metric"])
    print(result["direction"])
    print(result["impact"])
    print(result["statement"])
```

Possible statistical directions:

- `increase`
- `decrease`
- `inconclusive`
- `no_observed_difference`
- `unavailable`
- `invalid`

Possible performance impacts include improvement, degradation, and context-dependent changes.

An increase or decrease is identified when the paired confidence interval excludes zero. An interval containing zero is classified as inconclusive.

### 5.5. Accessing Capacity Findings

```python
for configuration in report["capacity_findings"]:
    print(configuration["link_1"]["findings"])
    print(configuration["link_2"]["findings"])
    print(configuration["bottleneck"]["statement"])
```

Capacity findings distinguish between theoretical overload, imbalance-induced bottlenecks, capacity limits, and configurations without theoretical overload.

## 6. Recommended GUI Integration

Two workflows are supported by the analysis modules.

### Individual Simulation

```text
Simulation Engine
    -> Performance Metrics
    -> GUI Visualization
```

Use `run_simulation()` and `calculate_metrics()` to obtain results for an individual configuration.

### Experimental Analysis

```text
Batch Experiments
    -> Statistical Analysis
    -> Automated Report Generation
    -> GUI Visualization
```

Use the existing CSV and JSON files to display completed experimental results.

Suggested GUI components:

- Simulation parameter inputs
- Individual and aggregate performance metrics
- Throughput, delay, loss, and utilization graphs
- Statistical summaries with confidence intervals
- Baseline comparison tables
- Automated research findings
- Capacity and bottleneck assessments
- Configuration filters

The GUI layout and presentation are independent of the analysis modules.

## 7. Important Considerations

- Traffic splits are stored as proportions. For example, `0.7` represents a 70/30 distribution.
- Absolute differences between percentage-based metrics are expressed in percentage points.
- Aggregate utilization is normalized across both links.
- Throughput and utilization are measured within the observation period.
- Average delay includes accepted frames completed during the drain period.
- Frame records should not be used to calculate performance metrics because record collection may be capped.
- Inconclusive statistical comparisons do not establish equivalent performance.
- Confidence intervals are individual 95% intervals without adjustment for multiple comparisons.
- The automated report analyzes batch experimental results rather than individual simulation runs.
- Report generation parameters must correspond to the parameters used to produce the experimental data.
- The statistical pipeline currently expects the defined experimental configurations and ten runs per configuration.
- Arbitrary experimental configurations and malformed input files are not fully supported or tested.
- The GUI should avoid rerunning the entire experimental pipeline whenever a user changes a display filter.

## 8. Regenerating All Experimental Outputs

Run the following commands in order from the project root:

```bash
python experiments.py
python statistical_analysis.py
python report_generator.py
```

Expected output files:

```text
results/
    experimental_results.csv
    statistical_summary.csv
    baseline_comparison.csv