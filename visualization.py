import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# Consistent colors throughout the dashboard.
BLUE = "#2878B5"
ORANGE = "#F28E2B"
GREEN = "#2E9D69"
PURPLE = "#8064A2"

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "figure.facecolor": "white",
    "axes.facecolor": "#FAFAFA",
})


METRICS = [
    ("throughput_mbps", "Throughput (Mbps)"),
    ("average_delay_ms", "Average Frame Delay (ms)"),
    ("frame_loss_percent", "Frame Loss (%)"),
    ("utilization_percent", "Link Utilization (%)"),
]


def show_chart(fig):
    """Display and release a Matplotlib figure."""
    fig.tight_layout()
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def empty_chart(message):
    """Display a readable message instead of an empty chart."""
    st.info(message)


def plot_link_comparison(df):
    """Compare Link 1 and Link 2 across four performance metrics."""

    if df.empty:
        empty_chart("No link performance data is available.")
        return

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))

    for ax, (metric, title) in zip(axes.flat, METRICS):
        columns = [f"link_1_{metric}", f"link_2_{metric}"]

        if not all(column in df.columns for column in columns):
            ax.text(0.5, 0.5, "Unavailable", ha="center", va="center")
            ax.set_title(title)
            continue

        values = df[columns].mean().tolist()

        ax.bar(
            ["Link 1", "Link 2"],
            values,
            color=[BLUE, ORANGE],
            width=0.55,
        )

        ax.set_title(title, fontweight="bold")
        ax.set_ylabel(title)
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)

    show_chart(fig)


def plot_load_comparison(df):
    """Compare aggregate performance across traffic distributions."""

    if df.empty:
        empty_chart("No comparison data is available.")
        return

    aggregate_metrics = [
        ("aggregate_throughput_mbps", "Aggregate Throughput (Mbps)"),
        ("aggregate_average_delay_ms", "Average Frame Delay (ms)"),
        ("aggregate_frame_loss_percent", "Frame Loss (%)"),
        ("aggregate_utilization_percent", "Aggregate Utilization (%)"),
    ]

    colors = [BLUE, ORANGE, GREEN, PURPLE]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    for ax, (metric, title) in zip(axes.flat, aggregate_metrics):
        if metric not in df.columns:
            ax.text(0.5, 0.5, "Unavailable", ha="center", va="center")
            ax.set_title(title)
            continue

        for (split, group), color in zip(
            df.groupby("traffic_split"),
            colors * len(df["traffic_split"].unique()),
        ):
            values = group.groupby("total_load_mbps")[metric].mean()

            ax.plot(
                values.index,
                values.values,
                marker="o",
                markersize=6,
                linewidth=2,
                color=color,
                label=f"{split * 100:.0f}/{(1-split) * 100:.0f}",
            )

        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Offered Load (Mbps)")
        ax.set_ylabel(title)
        ax.legend(title="Traffic Split", fontsize=8)
        ax.grid(alpha=0.2)
        ax.set_axisbelow(True)

    show_chart(fig)


def plot_confidence_intervals(summary):
    """Display sample means and their 95% confidence intervals."""

    metrics = [
        "aggregate_throughput_mbps",
        "aggregate_average_delay_ms",
        "aggregate_frame_loss_percent",
        "aggregate_utilization_percent",
    ]

    if summary.empty:
        empty_chart("No statistical results are available.")
        return

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    for ax, metric in zip(axes.flat, metrics):
        row = summary[summary["metric"] == metric].copy()

        ax.set_title(
            metric.replace("_", " ").title(),
            fontweight="bold",
        )

        required = {"mean", "ci_lower", "ci_upper", "traffic_split"}

        if row.empty or not required.issubset(row.columns):
            ax.text(0.5, 0.5, "Unavailable", ha="center", va="center")
            continue

        row = row.dropna(subset=["mean", "ci_lower", "ci_upper"])

        if row.empty:
            ax.text(0.5, 0.5, "Unavailable", ha="center", va="center")
            continue

        row = row.sort_values("traffic_split")
        means = row["mean"].to_numpy()
        lower = row["ci_lower"].to_numpy()
        upper = row["ci_upper"].to_numpy()

        # Avoid invalid error bars if an interval is malformed.
        if ((lower > means) | (upper < means)).any():
            ax.text(0.5, 0.5, "Invalid confidence interval", ha="center")
            continue

        positions = range(len(row))

        ax.errorbar(
            positions,
            means,
            yerr=[means - lower, upper - means],
            fmt="o",
            markersize=7,
            capsize=5,
            linewidth=2,
            color=BLUE,
        )

        ax.set_xticks(list(positions))
        ax.set_xticklabels([
            f"{split * 100:.0f}/{(1-split) * 100:.0f}"
            for split in row["traffic_split"]
        ])

        ax.set_xlabel("Traffic Distribution")
        ax.set_ylabel("Mean ± 95% CI")
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)

    show_chart(fig)
