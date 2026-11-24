# Integration contract

```python
from simulation import run_simulation
r = run_simulation(total_load_mbps=120, traffic_split=.9, seed=1)
```

Split is the fraction assigned to link 1, not a percentage. Official settings are in config.py. Optional parameters are link_capacity_mbps, payload_bytes, occupancy_byte_times, buffer_capacity, duration, record_limit, queue_sample_interval, base_epoch. Use defaults for official experiments. The returned dictionary contains config, run_id, base_epoch, observation_duration, drain_duration, link_1, link_2, counts, timing, frame_records, queue_records, records_truncated. Each link contains link_id, offered_load_mbps, counts, timing, max_queue_length. Top-level counts and timing are sums across links; timing.end_time is the final simulated time. All timing fields are seconds; busy time includes IFG. Aggregate busy time can reach twice the observation duration.

Counts: generated, accepted, dropped, completed_within_observation, completed_total, completed_during_drain, unfinished_at_observation. Timing: busy_time_observation, delay_sum_total, delay_count_total, delay_sum_observation, delay_count_observation, queue_delay_sum_total.

## Metrics handoff
For each link or aggregate, let c and t be counts and timing, T=observation_duration, P=config.payload_bytes, N=1 for a link or 2 for aggregate.

- Throughput Mbps = c.completed_within_observation * P * 8 / T / 1e6.
- Delay ms = 1000 * t.delay_sum_total / t.delay_count_total (undefined if no deliveries).
- Loss % = 100 * c.dropped / c.generated (undefined if no arrivals).
- Utilization % = 100 * t.busy_time_observation / (N*T).
- Queue delay ms = 1000 * t.queue_delay_sum_total / t.delay_count_total.

Do not compute metrics from capped records. Aggregate delay and loss are weighted by frame counts. Use run-level values for sample SD and t confidence intervals; 10 seeds per scenario, t critical 2.262 for df=9. Compare splits at fixed load. No statistical claims from the fixture.

## GUI handoff
Use link_1 and link_2 for separate displays; queue_records contains sim_time_s, link_id, waiting_frames, busy. Frame records contain arrival, start and completion in both simulation and epoch seconds, delays, queue length at arrival, status, drop_reason, and observation completion flag. Dropped frames have null start/completion/delay. CSV export should preserve fractional seconds and blank nulls. Warn if records_truncated is true. Full frame export requires record_limit=None; use only for individual runs. The engine is synchronous; show a spinner during execution. Keep batch experiment mode separate.

## Acceptance checks
Generated = accepted + dropped; accepted = completed_total after drain; waiting occupancy <= capacity; per-link busy time <= T (allow floating point tolerance); FIFO order; no arrivals at or after T; dropped records have full waiting buffer; identical seeds reproduce simulated results, not absolute epochs unless base_epoch is fixed.
