import matplotlib.pyplot as plt
import pandas as pd


def plot_frame_counts(simulation_results):
    counts = simulation_results["counts"]

    labels = ["Generated", "Accepted", "Dropped"]
    values = [
        counts["generated"],
        counts["accepted"],
        counts["dropped"]
    ]

    fig, ax = plt.subplots(figsize=(8, 4))

    ax.bar(labels, values)

    ax.set_title("Ethernet Frame Statistics")
    ax.set_ylabel("Number of Frames")
    ax.set_xlabel("Frame Status")

    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()

    return fig


def plot_delay_distribution(simulation_results):
    records = simulation_results["records"]

    df = pd.DataFrame(records)

    fig, ax = plt.subplots(figsize=(8, 4))

    if not df.empty:
        delivered = df[df["status"] == "delivered"].copy()

        if not delivered.empty:
            delivered["delay_ms"] = (
                delivered["completion_time"] -
                delivered["arrival_time"]
            ) * 1000

            ax.hist(delivered["delay_ms"], bins=20)

            ax.set_title("Frame Delay Distribution")
            ax.set_xlabel("Frame Delay (ms)")
            ax.set_ylabel("Number of Frames")
        else:
            ax.text(
                0.5, 0.5,
                "No successfully delivered frames in recorded sample",
                ha="center",
                va="center",
                transform=ax.transAxes
            )
    else:
        ax.text(
            0.5, 0.5,
            "No frame records available",
            ha="center",
            va="center",
            transform=ax.transAxes
        )

    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()

    return fig