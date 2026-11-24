# NSCOM03 - NSS Research Project

# Ethernet Traffic Imbalance Simulator

Research: Performance Analysis of Traffic Imbalance in Aggregated Ethernet Links Using Discrete-Event Simulation.

This engine models two independent, one-direction transmission paths of full-duplex Ethernet links. It is not a complete IEEE 802.1AX implementation. It excludes dynamic redistribution, flow hashing, MAC learning, PAUSE, retransmissions, propagation and processing delays, collisions and physical errors. The original project's documented counters and observation/drain convention are retained; the original Python source was not available for direct patching.

## Setup
Python 3.10+; from this directory:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python demo.py --load 120 --split 0.9 --seed 1
```

For a full frame export add `--all-frames`. Default export retains the first 10,000 arrivals only; counters always cover the entire run. For batch experiments use `record_limit=0, queue_sample_interval=None` to avoid unnecessary memory usage. No GUI or statistical runner is included in this engine package.

## Model
Two 100 Mbps links; 1500-byte payload; 1538 byte-times (1500 payload + 14 header + 4 FCS + 8 preamble/SFD + 12 IFG). Service time is 123.04 microseconds, delivery time 122.08 microseconds. Effective payload capacity is 97.529 Mbps per link. Each link has its own independent exponential interarrival stream and FIFO waiting queue of 100 frames, excluding the frame in service. Arrival rate = assigned payload Mbps × 1e6 / 12000. Idle links admit immediately; busy links queue if space exists; only a full waiting buffer causes tail drop. Link speed remains constant. No traffic is reassigned.

Official runs: loads 80, 120, 160 Mbps crossed with splits 50/50, 70/30, 90/10; seeds 1–10; 60 seconds, empty initial queues, no warm-up. Each seed is reused across scenarios (comparisons may be paired by seed); streams within a run are distinct. Arrivals stop before t=60; accepted frames drain. Completion at t=60 counts in observation. Drain duration includes any final IFG. Queue samples are instantaneous at 10 ms intervals, not exact maxima; exact maximum waiting occupancy is separately returned.

Epoch mapping: base_epoch is captured once at run start (or supplied for deterministic testing). Each event epoch = base_epoch + simulated event time, in fractional Unix seconds UTC. These are synthetic timestamps, not captured traffic or wall-clock execution times. Calculate delays using simulated seconds, not epoch differences.

## Files
- simulation.py: reusable SimPy engine
- config.py: official constants
- demo.py: standalone CSV/JSON export demonstration
- tests/: engine checks
- INTEGRATION_GUIDE.md: shared API and formulas
- METHODOLOGY.md: paper-ready technical methodology
- samples/: illustrative schema fixture, not measured results
- methodology.pptx: methodology contribution

## Verification status
Python syntax compilation was performed. SimPy was unavailable in the preparation environment and installation could not reach the package index; the actual SimPy tests and demo have not been executed here. Run the commands above locally before integration or reporting results. The supplied fixture is illustrative only.
