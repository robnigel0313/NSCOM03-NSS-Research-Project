import streamlit as st
import pandas as pd

from simulation import run_simulation
from metrics import calculate_metrics
from visualization import (
    plot_frame_counts,
    plot_delay_distribution
)


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Ethernet Network Simulator",
    page_icon="🌐",
    layout="wide"
)


# --------------------------------------------------
# APPLICATION HEADER
# --------------------------------------------------

st.title("🌐 Ethernet Network Simulator")

st.write(
    "An interactive Ethernet simulator that evaluates "
    "network performance under different traffic loads."
)

st.divider()


# --------------------------------------------------
# SIMULATION SETTINGS
# --------------------------------------------------

st.sidebar.header("Simulation Configuration")

link_speed = st.sidebar.selectbox(
    "Ethernet Link Speed",
    options=[10, 100, 1000],
    format_func=lambda x: (
        f"{x} Mbps" if x != 1000 else "1 Gbps (1000 Mbps)"
    )
)

offered_load = st.sidebar.number_input(
    "Offered Traffic Load (Mbps)",
    min_value=0.0,
    max_value=2000.0,
    value=50.0,
    step=10.0
)

seed = st.sidebar.number_input(
    "Random Seed",
    min_value=0,
    max_value=999999,
    value=42,
    step=1
)

duration = st.sidebar.number_input(
    "Observation Period (seconds)",
    min_value=0.1,
    max_value=60.0,
    value=60.0,
    step=1.0
)

st.sidebar.caption(
    "The default observation period is 60 seconds."
)

run_button = st.sidebar.button(
    "▶ Run Simulation",
    type="primary",
    use_container_width=True
)


# --------------------------------------------------
# SIMULATION EXECUTION
# --------------------------------------------------

if run_button:

    try:
        with st.spinner("Running Ethernet simulation..."):

            simulation_results = run_simulation(
                link_speed=link_speed,
                offered_load=offered_load,
                seed=int(seed),
                duration=duration,
                record_limit=10000
            )

            metrics = calculate_metrics(simulation_results)

        st.success("Simulation completed successfully!")

        # ------------------------------------------
        # SIMULATION SUMMARY
        # ------------------------------------------

        st.header("Simulation Results")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Payload Throughput",
            f"{metrics['throughput_mbps']:.2f} Mbps"
        )

        delay = metrics["average_delay_ms"]

        col2.metric(
            "Average Frame Delay",
            f"{delay:.4f} ms" if delay is not None else "N/A"
        )

        col3.metric(
            "Frame Loss",
            f"{metrics['frame_loss_percent']:.2f}%"
        )

        col4.metric(
            "Link Utilization",
            f"{metrics['utilization_percent']:.2f}%"
        )

        st.divider()

        # ------------------------------------------
        # CONFIGURATION INFORMATION
        # ------------------------------------------

        st.subheader("Simulation Configuration")

        config_col1, config_col2, config_col3 = st.columns(3)

        config_col1.write(f"**Link Speed:** {link_speed} Mbps")
        config_col2.write(f"**Offered Load:** {offered_load} Mbps")
        config_col3.write(f"**Random Seed:** {seed}")

        # ------------------------------------------
        # FRAME STATISTICS
        # ------------------------------------------

        st.subheader("Frame Statistics")

        counts = simulation_results["counts"]

        count_col1, count_col2, count_col3 = st.columns(3)

        count_col1.metric(
            "Generated Frames",
            f"{counts['generated']:,}"
        )

        count_col2.metric(
            "Accepted Frames",
            f"{counts['accepted']:,}"
        )

        count_col3.metric(
            "Dropped Frames",
            f"{counts['dropped']:,}"
        )

        st.write(
            f"Successfully completed during observation: "
            f"{counts['completed_within_observation']:,}"
        )

        st.write(
            f"Successfully completed during drain: "
            f"{counts['completed_during_drain']:,}"
        )

        # ------------------------------------------
        # VISUALIZATIONS
        # ------------------------------------------

        st.divider()

        st.header("Performance Visualizations")

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader("Frame Statistics")

            frame_fig = plot_frame_counts(simulation_results)

            st.pyplot(frame_fig)

        with chart_col2:
            st.subheader("Frame Delay Distribution")

            delay_fig = plot_delay_distribution(simulation_results)

            st.pyplot(delay_fig)

        # ------------------------------------------
        # FRAME RECORDS
        # ------------------------------------------

        st.divider()

        st.subheader("Simulation Frame Records")

        records_df = pd.DataFrame(
            simulation_results["records"]
        )

        if not records_df.empty:

            st.dataframe(
                records_df,
                use_container_width=True
            )

            csv_data = records_df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Download Frame Records (CSV)",
                data=csv_data,
                file_name="ethernet_simulation_results.csv",
                mime="text/csv"
            )

        else:
            st.info("No frame records were generated.")

        if simulation_results["records_truncated"]:
            st.warning(
                "Only the first 10,000 frame records are displayed. "
                "The performance metrics still account for all frames."
            )

        # ------------------------------------------
        # SIMULATION DETAILS
        # ------------------------------------------

        with st.expander("View Detailed Simulation Information"):

            st.write("**Timing Information**")

            st.json(simulation_results["timing"])

            st.write("**Simulation Counts**")

            st.json(counts)

    except Exception as e:

        st.error(f"Simulation error: {e}")


else:

    st.info(
        "Configure the Ethernet link speed and offered traffic load "
        "using the sidebar, then click Run Simulation."
    )

    st.subheader("Available Performance Metrics")

    st.write("""
    - **Payload Throughput:** Amount of successfully delivered payload data per second.
    - **Average Frame Delay:** Average time required for successfully delivered frames.
    - **Frame Loss:** Percentage of generated frames dropped because of buffer limitations.
    - **Link Utilization:** Percentage of the observation period during which the link is occupied.
    """)