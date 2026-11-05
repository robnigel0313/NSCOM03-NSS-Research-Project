# NSCOM03 - NSS Research Project
# Ethernet Network Performance Simulator

## Project background

**Research title:** *Comparative Analysis of Ethernet Network Performance at Different Link Speeds Using a Python-Based Interactive Simulator*

This Network Simulation Study (NSS) project examines how Ethernet link speed and offered traffic load affect network performance. The group is developing an interactive Python simulator to compare **10 Mbps (10BASE-T), 100 Mbps (100BASE-TX), and 1 Gbps (1000BASE-T)** links under controlled traffic conditions. The proposed experiments use offered payload traffic loads of **5, 50, 200, and 1,200 Mbps** and evaluate **payload throughput, average frame delay, frame loss, and link utilization**.

The simulator uses **SimPy** to model frame arrivals, FIFO queueing, transmission, and buffer-overflow drops; **Streamlit** provides the user interface, while **Pandas** and **Matplotlib** support results analysis and visualization. It is a simplified, full-duplex point-to-point Ethernet model intended for educational comparison, **not** a physical network measurement or a full Ethernet protocol emulator.

**This repository currently contains the core simulation engine**, which generates the records and aggregate counters needed by the performance metrics module and the Streamlit application. The immediate group goal is a working integrated code demonstration on **November 6, 2026**.

## Project structure

The repository currently contains the simulation engine and its supporting files:

```text
ethernet_simulator/
├── simulation.py          # SimPy-based Ethernet simulation engine
├── demo.py                # Standalone command-line demonstration
├── requirements.txt       # Current Python dependency list
├── README.md              # Project overview and setup instructions
└── tests/
    └── test_simulation.py # Automated simulation tests
```

As the project is integrated, the planned application structure is:

```text
ethernet_simulator/
├── main.py                # Streamlit application (planned)
├── simulation.py          # Ethernet simulation engine
├── metrics.py             # Performance calculations (planned)
├── visualization.py       # Graphs and plots (planned)
├── demo.py                # Standalone simulation demonstration
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
└── tests/
    └── test_simulation.py # Simulation tests
```

The files labeled **planned** are not included in this engine-only package. They will be added during integration. The dependency list will also be expanded when the interface and analysis modules are added.

## Install and run (Windows CMD or terminal)
```bash
cd ethernet_simulator
python -m pip install -r requirements.txt
python demo.py
python -m unittest discover -s tests -v
python -m streamlit run main.py
```

## Simulation API and integration
```python
from simulation import run_simulation
result = run_simulation(link_speed=100, offered_load=50, seed=42)
# Optional: duration=60.0, buffer_capacity=100, record_limit=10000
```

`link_speed` must be 10, 100 or 1000 Mbps. `offered_load` is a **target payload traffic rate** in Mbps; realized generated traffic varies slightly with the random arrival process. Random seeds make runs reproducible.

`result` contains:
- `config`: selected inputs and byte/timing constants.
- `counts`: `generated`, `accepted`, `dropped`, `completed_within_observation`, `completed_total`, `completed_during_drain`, `unfinished_at_observation`.
- `timing`: `busy_time_observation`, `delay_sum_total`, `delay_count_total`, `delay_sum_observation`, `delay_count_observation`, `end_time` (seconds).
- `records`: up to the first `record_limit` generated frames (delivered/dropped), with `frame_id`, `arrival_time`, `transmission_start`, `completion_time`, `status`, `payload_bytes`.
- `records_truncated`: true when generated frame count exceeds the record cap.

### Metrics calculation contract
```python
cfg, c, t = result['config'], result['counts'], result['timing']
seconds = cfg['duration_seconds']
throughput_mbps = c['completed_within_observation'] * cfg['payload_bytes'] * 8 / seconds / 1e6
average_delay_ms = t['delay_sum_total'] / t['delay_count_total'] * 1000 if t['delay_count_total'] else 0.0
loss_percent = c['dropped'] / c['generated'] * 100 if c['generated'] else 0.0
utilization_percent = t['busy_time_observation'] / seconds * 100
```
The metrics module must use **aggregate counts/timing**, not `records`, which may be capped. Delay includes accepted frames completed during drain; throughput and utilization use the 60-second observation only. `unfinished_at_observation` is **not** packet loss.

### Model details
- 1500-byte payload + 18-byte MAC header/FCS + 8-byte preamble/SFD = **1526 transmitted bytes**.
- 12-byte-time interframe gap (IFG) is modeled as separate reserved link time, **not transmitted bytes**.
- Total service occupancy is 1538 byte-times per frame.
- Completion timestamp occurs at the end of frame transmission, **before** IFG.
- FIFO queue holds at most 100 **waiting** frames; the in-service frame is excluded.
- Arrivals stop at `duration`; the transmitter drains accepted frames afterward.
- Zero offered traffic produces zero frames; deterministic frame length; Poisson arrival times.
- No real physical-layer signals, collisions, retransmissions, errors, or TCP.

### Performance caution
At 1200 Mbps for 60 seconds, the arrival generator creates roughly **6 million frames per run**. That is a large SimPy workload, especially for 10 repetitions and all three link speeds. For the November 6 demo, start with `duration=0.5` or `duration=1` and moderate offered loads; use 60 seconds for the formal experiments after profiling. The record cap prevents retaining millions of dictionaries but does not eliminate event-processing CPU cost.

### Integration
Copy `simulation.py` to the group project's root next to `metrics.py` and `main.py`. Keep `run_simulation` and the result keys stable when connecting the metrics and interface modules.
