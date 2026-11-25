import streamlit as st
import pandas as pd
import time

from config import LOADS, SPLITS, SEEDS, DEFAULTS
from experiments import run_experiments
from statistical_analysis import METRIC_COLUMNS, calculate_statistics
from visualization import (
    plot_link_comparison,
    plot_load_comparison,
    plot_confidence_intervals,
)

st.set_page_config(
    page_title="Ethernet Traffic Imbalance Simulator",
    page_icon="🌐",
    layout="wide",
)

# ---------------- SESSION STATE ----------------

for key in ("results", "summary", "paired", "baseline", "settings"):
    st.session_state.setdefault(key, None)

# ---------------- HELPER FUNCTIONS ----------------

def split_label(split):
    return f"{split * 100:.0f}/{(1 - split) * 100:.0f}"

def summarize(results):
    df = pd.DataFrame(results)
    rows = []

    for (load, split), group in df.groupby(
        ["total_load_mbps", "traffic_split"]
    ):
        for metric in METRIC_COLUMNS:
            stats = calculate_statistics(group[metric].tolist())
            rows.append({
                "total_load_mbps": load,
                "traffic_split": split,
                "metric": metric,
                **stats,
            })

    return pd.DataFrame(rows)

def compare_results(results):
    df = pd.DataFrame(results)
    groups = {
        key: group.set_index("seed")
        for key, group in df.groupby(
            ["total_load_mbps", "traffic_split"]
        )
    }

    paired, baseline = [], []

    for (load, split), current in groups.items():
        if split == 0.5 or (load, 0.5) not in groups:
            continue

        reference = groups[(load, 0.5)]

        common_seeds = current.index.intersection(reference.index)
        if len(common_seeds) != len(current) or len(common_seeds) != len(reference):
            continue

        current = current.loc[common_seeds]
        reference = reference.loc[common_seeds]

        for metric in METRIC_COLUMNS:
            differences = (
                current[metric] - reference[metric]
            ).tolist()

            stats = calculate_statistics(differences)
            baseline_mean = reference[metric].mean()
            current_mean = current[metric].mean()

            paired.append({
                "total_load_mbps": load,
                "baseline_split": 0.5,
                "traffic_split": split,
                "metric": metric,
                **stats,
            })

            baseline.append({
                "total_load_mbps": load,
                "baseline_split": 0.5,
                "traffic_split": split,
                "metric": metric,
                "baseline_mean": baseline_mean,
                "current_mean": current_mean,
                "difference": stats["mean"],
                "percent_change": (
                    (current_mean - baseline_mean)
                    / abs(baseline_mean) * 100
                    if baseline_mean != 0 else None
                ),
            })

    return pd.DataFrame(paired), pd.DataFrame(baseline)

# ---------------- SIDEBAR ----------------

st.sidebar.title("Simulation Settings")

loads = st.sidebar.multiselect(
    "Total offered load (Mbps)",
    LOADS,
    default=list(LOADS),
)

splits = st.sidebar.multiselect(
    "Traffic distribution",
    SPLITS,
    default=list(SPLITS),
    format_func=split_label,
)

duration = st.sidebar.number_input(
    "Simulation duration (seconds)",
    min_value=1,
    max_value=600,
    value=DEFAULTS["duration"],
)

buffer_size = st.sidebar.number_input(
    "Waiting buffer (frames)",
    min_value=0,
    max_value=10000,
    value=DEFAULTS["buffer_capacity"],
)

capacity = st.sidebar.number_input(
    "Link capacity (Mbps)",
    min_value=1,
    max_value=10000,
    value=DEFAULTS["link_capacity_mbps"],
)

total_runs = len(loads) * len(splits) * len(SEEDS)

st.sidebar.info(
    f"Each configuration uses {len(SEEDS)} random seeds."
)

st.sidebar.metric("Total simulation runs", total_runs)

run = st.sidebar.button(
    "▶ Run Experiments",
    type="primary",
    use_container_width=True,
    disabled=not loads or not splits,
)

# ---------------- HEADER ----------------

st.title("Ethernet Traffic Imbalance Simulator")

st.markdown(
    """
    **Performance Analysis of Traffic Imbalance in Aggregated Ethernet Links
    Using Discrete-Event Simulation**
    """
)

# ---------------- EXPERIMENT EXECUTION ----------------

if run:
    settings = DEFAULTS.copy()
    settings.update({
        "duration": float(duration),
        "buffer_capacity": int(buffer_size),
        "link_capacity_mbps": int(capacity),
    })

    progress = st.progress(0)
    status = st.empty()
    details = st.empty()
    start_time = time.perf_counter()

    def update_progress(completed, total, message=""):
        progress.progress(min(completed / total, 1.0))
        status.info(f"Simulation progress: {completed}/{total}")
        
    try:
        status.info(f"Running {total_runs} simulations...")

        results = run_experiments(
            loads=loads,
            splits=splits,
            seeds=SEEDS,
            settings=settings,
            progress_callback=update_progress,
        )

        status.info("Calculating statistical summaries...")
        progress.progress(0.95)

        summary = summarize(results)
        paired, baseline = compare_results(results)

        st.session_state.results = pd.DataFrame(results)
        st.session_state.summary = summary
        st.session_state.paired = paired
        st.session_state.baseline = baseline
        st.session_state.settings = settings

        progress.progress(1.0)
        status.success(
            f"Completed {len(results)} simulations in "
            f"{time.perf_counter() - start_time:.2f} seconds!"
        )

    except Exception as error:
        status.error(f"Experiment failed: {error}")
        st.exception(error)

    finally:
        details.empty()

# ---------------- RESULTS ----------------

if st.session_state.results is None:
    st.info("👈 Configure your simulation in the sidebar and click Run Experiments.")

    st.subheader("Experimental Matrix")

    matrix = pd.DataFrame({
        "Total Load (Mbps)": LOADS,
        "50/50": ["40 / 40", "60 / 60", "80 / 80"],
        "70/30": ["56 / 24", "84 / 36", "112 / 48"],
        "90/10": ["72 / 8", "108 / 12", "144 / 16"],
    })

    st.dataframe(matrix, use_container_width=True, hide_index=True)
    st.stop()

results = st.session_state.results
summary = st.session_state.summary

# ---------------- CONFIGURATION SELECTION ----------------

st.divider()
st.header("📊 Performance Dashboard")

col1, col2 = st.columns(2)

with col1:
    selected_load = st.selectbox(
        "Offered Load (Mbps)",
        sorted(results["total_load_mbps"].unique()),
    )

with col2:
    selected_split = st.selectbox(
        "Traffic Distribution",
        sorted(results["traffic_split"].unique()),
        format_func=split_label,
    )

selected = results[
    (results["total_load_mbps"] == selected_load)
    & (results["traffic_split"] == selected_split)
]

selected_stats = summary[
    (summary["total_load_mbps"] == selected_load)
    & (summary["traffic_split"] == selected_split)
]

# ---------------- DASHBOARD TABS ----------------

overview, links, comparison, statistics, data = st.tabs([
    "📌 Overview",
    "🔗 Link Performance",
    "⚖️ Traffic Comparison",
    "📈 Statistics",
    "📁 Data & Export",
])

# ---------------- OVERVIEW ----------------

with overview:
    st.subheader("Aggregate Performance")

    metrics = [
        ("Throughput", "aggregate_throughput_mbps", "Mbps"),
        ("Average Delay", "aggregate_average_delay_ms", "ms"),
        ("Frame Loss", "aggregate_frame_loss_percent", "%"),
        ("Utilization", "aggregate_utilization_percent", "%"),
    ]

    columns = st.columns(4)

    for column, (label, metric, unit) in zip(columns, metrics):
        value = selected[metric].mean()
        column.metric(
            label,
            "N/A" if pd.isna(value) else f"{value:.3f} {unit}",
        )

    st.subheader("Traffic Assignment")

    c1, c2 = st.columns(2)

    c1.metric(
        "Link 1 Offered Load",
        f"{selected_load * selected_split:.2f} Mbps",
    )

    c2.metric(
        "Link 2 Offered Load",
        f"{selected_load * (1 - selected_split):.2f} Mbps",
    )

    st.subheader("Link Performance")
    plot_link_comparison(selected)

# ---------------- LINK PERFORMANCE ----------------

with links:
    st.subheader("Link 1 vs Link 2")
    plot_link_comparison(selected)

    st.subheader("Detailed Metrics")

    metric_names = [
        "throughput_mbps",
        "average_delay_ms",
        "frame_loss_percent",
        "utilization_percent",
        "average_queue_delay_ms",
    ]

    table = [{
        "Metric": metric.replace("_", " ").title(),
        "Link 1": selected[f"link_1_{metric}"].mean(),
        "Link 2": selected[f"link_2_{metric}"].mean(),
    } for metric in metric_names]

    st.dataframe(
        pd.DataFrame(table),
        use_container_width=True,
        hide_index=True,
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Link 1 Maximum Queue",
        f"{selected['link_1_max_queue_length'].mean():.2f} frames",
    )

    c2.metric(
        "Link 2 Maximum Queue",
        f"{selected['link_2_max_queue_length'].mean():.2f} frames",
    )

# ---------------- TRAFFIC COMPARISON ----------------

with comparison:
    st.subheader("Effect of Traffic Distribution")
    plot_load_comparison(results)

    st.subheader("Utilization Gap")

    gap = results.pivot_table(
        index="total_load_mbps",
        columns="traffic_split",
        values="utilization_gap_pp",
        aggfunc="mean",
    )

    gap.columns = [split_label(x) for x in gap.columns]

    st.line_chart(
        gap,
        x_label="Offered Load (Mbps)",
        y_label="Utilization Gap (percentage points)",
    )

    st.caption(
        "Utilization gap represents the absolute difference "
        "between the two links' utilization percentages."
    )

    st.subheader("Comparison Against Balanced Traffic")

    baseline = st.session_state.baseline

    if not baseline.empty:
        st.dataframe(
            baseline,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Balanced 50/50 traffic is needed for baseline comparisons.")

# ---------------- STATISTICAL ANALYSIS ----------------

with statistics:
    st.subheader("95% Confidence Intervals")
    plot_confidence_intervals(selected_stats)

    st.subheader("Statistical Summary")

    st.dataframe(
        selected_stats,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Paired Comparisons")

    paired = st.session_state.paired

    if not paired.empty:
        paired_selected = paired[
            (paired["total_load_mbps"] == selected_load)
            & (paired["traffic_split"] == selected_split)
        ]

        st.dataframe(
            paired_selected,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Paired comparisons require a 50/50 baseline.")

    st.caption(
        "Confidence intervals use a two-sided 95% t-interval. "
        "An interval containing zero does not establish equivalence."
    )

# ---------------- DATA & EXPORT ----------------

with data:
    st.subheader("Experimental Results")

    st.dataframe(
        results,
        use_container_width=True,
        hide_index=True,
    )

    exports = {
        "Experimental Results": (results, "experimental_results.csv"),
        "Statistical Summary": (summary, "statistical_summary.csv"),
        "Baseline Comparison": (
            st.session_state.baseline,
            "baseline_comparison.csv",
        ),
        "Paired Comparison": (
            st.session_state.paired,
            "paired_comparison.csv",
        ),
    }

    for label, (frame, filename) in exports.items():
        st.download_button(
            f"⬇️ Download {label}",
            frame.to_csv(index=False).encode("utf-8"),
            file_name=filename,
            mime="text/csv",
            key=filename,
        )

    st.subheader("Simulation Parameters")
    st.json(st.session_state.settings)