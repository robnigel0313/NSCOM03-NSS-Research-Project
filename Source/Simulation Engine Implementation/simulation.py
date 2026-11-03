"""Member 1: discrete-event Ethernet link simulation (SimPy).

Public API: run_simulation(link_speed, offered_load, seed=42, ...).
Units: Mbps denotes *payload* offered load; all times are seconds.
The simulated transmitter is a single, error-free full-duplex Ethernet egress link.

The 100-frame FIFO capacity applies to WAITING frames only; the currently
transmitting frame is not counted. The arrival generator runs for the
observation period, then the transmitter drains all accepted frames.

Frames finish transmitting after the preamble, SFD, MAC frame and FCS have
been sent (1526 bytes for a 1500-byte payload). A 12-byte-time interframe
spacing is reserved between frames. We model the spacing as a separate
link-occupancy phase after each frame; the delivery timestamp excludes it.
"""
from __future__ import annotations

from collections import deque
import math
import random
from typing import Any

try:
    import simpy
except ImportError:  # Clear error on invocation, rather than an obscure failure.
    simpy = None

PAYLOAD_BYTES = 1500
MAC_OVERHEAD_BYTES = 18  # 14-byte header + 4-byte FCS
PREAMBLE_SFD_BYTES = 8
IFG_BYTES = 12  # idle time, represented in byte-times; NOT transmitted bytes
FRAME_WIRE_BYTES = PAYLOAD_BYTES + MAC_OVERHEAD_BYTES + PREAMBLE_SFD_BYTES
FRAME_OCCUPANCY_BYTES = FRAME_WIRE_BYTES + IFG_BYTES
SUPPORTED_LINK_SPEEDS = (10, 100, 1000)
DEFAULT_BUFFER_CAPACITY = 100
DEFAULT_DURATION = 60.0


def _validate(link_speed: float, offered_load: float, seed: int,
              duration: float, buffer_capacity: int, record_limit: int) -> None:
    if isinstance(link_speed, bool) or link_speed not in SUPPORTED_LINK_SPEEDS:
        raise ValueError('link_speed must be one of 10, 100, or 1000 Mbps')
    if isinstance(offered_load, bool) or not isinstance(offered_load, (int, float)) or not math.isfinite(offered_load) or offered_load < 0:
        raise ValueError('offered_load must be a finite, nonnegative Mbps value')
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError('seed must be an integer')
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('duration must be finite and greater than zero')
    if isinstance(buffer_capacity, bool) or not isinstance(buffer_capacity, int) or buffer_capacity < 0:
        raise ValueError('buffer_capacity must be a nonnegative integer')
    if isinstance(record_limit, bool) or not isinstance(record_limit, int) or record_limit < 0:
        raise ValueError('record_limit must be a nonnegative integer')


def run_simulation(
    link_speed: int,
    offered_load: float,
    seed: int = 42,
    *,
    duration: float = DEFAULT_DURATION,
    buffer_capacity: int = DEFAULT_BUFFER_CAPACITY,
    record_limit: int = 10_000,
) -> dict[str, Any]:
    """Run a reproducible SimPy discrete-event simulation.

    Returns a plain dictionary consumed by Member 2's metrics.py:
      config: parameters and modeled sizes/times
      counts: generated, accepted, dropped, completed_within_observation,
              completed_total, completed_during_drain, unfinished_at_observation
      timing: busy_time_observation, delay_sum_total, delay_count_total,
              delay_sum_observation, delay_count_observation, end_time
      records: up to `record_limit` *first* frame records, including arrival,
               transmission_start, completion, and status ('delivered'/'dropped').
      records_truncated: True if some frame records were omitted.

    Records are bounded to avoid holding millions of Python dictionaries.
    All counts and sums cover EVERY frame, not merely sampled records.
    In overload, generating millions of frames can take significant time.
    """
    _validate(link_speed, offered_load, seed, duration, buffer_capacity, record_limit)
    if simpy is None:
        raise ImportError('SimPy is required: run `python -m pip install -r requirements.txt`')

    env = simpy.Environment()
    rng = random.Random(seed)
    speed_bps = link_speed * 1_000_000.0
    tx_seconds = FRAME_WIRE_BYTES * 8 / speed_bps
    ifg_seconds = IFG_BYTES * 8 / speed_bps
    arrival_rate = offered_load * 1_000_000.0 / (PAYLOAD_BYTES * 8)
    queue: deque[tuple[int, float]] = deque()
    records: list[dict[str, Any]] = []
    counts = {
        'generated': 0, 'accepted': 0, 'dropped': 0,
        'completed_within_observation': 0, 'completed_total': 0,
        'completed_during_drain': 0, 'unfinished_at_observation': 0,
    }
    timing = {
        'busy_time_observation': 0.0,
        'delay_sum_total': 0.0, 'delay_count_total': 0,
        'delay_sum_observation': 0.0, 'delay_count_observation': 0,
        'end_time': 0.0,
    }
    generator_done = False
    transmitting = False
    wakeup = env.event()

    def record(entry: dict[str, Any]) -> None:
        if len(records) < record_limit:
            records.append(entry)

    def transmitter():
        nonlocal transmitting, wakeup
        while True:
            if not queue:
                if generator_done:
                    return
                yield wakeup
                continue
            frame_id, arrival_time = queue.popleft()
            transmitting = True
            start_time = env.now
            # Physical frame transmission: delivery timestamp excludes IFG.
            yield env.timeout(tx_seconds)
            completion_time = env.now
            delay = completion_time - arrival_time
            counts['completed_total'] += 1
            timing['delay_sum_total'] += delay
            timing['delay_count_total'] += 1
            if completion_time <= duration:
                counts['completed_within_observation'] += 1
                timing['delay_sum_observation'] += delay
                timing['delay_count_observation'] += 1
            else:
                counts['completed_during_drain'] += 1
            # Records are sampled from first `record_limit` generated frames.
            # Avoid keeping all records for long simulations.
            if frame_id <= record_limit:
                record({
                    'frame_id': frame_id, 'arrival_time': arrival_time,
                    'transmission_start': start_time,
                    'completion_time': completion_time,
                    'status': 'delivered', 'payload_bytes': PAYLOAD_BYTES,
                })
            # Link occupancy is wire transmission plus the following IFG.
            # Clip each phase to the [0, duration] measurement window.
            timing['busy_time_observation'] += max(0.0, min(completion_time, duration) - min(start_time, duration))
            if ifg_seconds:
                yield env.timeout(ifg_seconds)
                timing['busy_time_observation'] += max(0.0, min(env.now, duration) - min(completion_time, duration))
            transmitting = False

    def arrival_generator():
        nonlocal generator_done, wakeup
        if arrival_rate > 0:
            while True:
                interval = rng.expovariate(arrival_rate)
                if env.now + interval >= duration:
                    break
                yield env.timeout(interval)
                counts['generated'] += 1
                frame_id = counts['generated']
                arrival_time = env.now
                # At most one in service; queue capacity counts WAITING only.
                # When idle, append and wake transmitter at the same timestamp.
                if transmitting and len(queue) >= buffer_capacity:
                    counts['dropped'] += 1
                    if frame_id <= record_limit:
                        record({'frame_id': frame_id, 'arrival_time': arrival_time,
                                'transmission_start': None, 'completion_time': None,
                                'status': 'dropped', 'payload_bytes': PAYLOAD_BYTES})
                elif not transmitting and queue and len(queue) >= buffer_capacity:
                    # Defensive: only possible with zero buffer and a pending
                    # wakeup. The first waiting frame occupies the service slot.
                    counts['dropped'] += 1
                    if frame_id <= record_limit:
                        record({'frame_id': frame_id, 'arrival_time': arrival_time,
                                'transmission_start': None, 'completion_time': None,
                                'status': 'dropped', 'payload_bytes': PAYLOAD_BYTES})
                else:
                    queue.append((frame_id, arrival_time))
                    counts['accepted'] += 1
                    if not transmitting and not wakeup.triggered:
                        wakeup.succeed()
                    if not transmitting:
                        wakeup = env.event()
        # Even at zero traffic, time advances to observation boundary.
        if env.now < duration:
            yield env.timeout(duration - env.now)
        counts['unfinished_at_observation'] = counts['accepted'] - counts['completed_within_observation']
        generator_done = True
        if not transmitting and not queue and not wakeup.triggered:
            wakeup.succeed()

    env.process(transmitter())
    env.process(arrival_generator())
    env.run()
    timing['end_time'] = env.now
    assert counts['generated'] == counts['accepted'] + counts['dropped']
    assert counts['accepted'] == counts['completed_total']
    assert counts['completed_total'] == counts['completed_within_observation'] + counts['completed_during_drain']
    assert counts['unfinished_at_observation'] == counts['completed_during_drain']
    assert timing['busy_time_observation'] <= duration + 1e-7

    return {
        'config': {
            'link_speed_mbps': link_speed,
            'offered_load_mbps': offered_load,
            'seed': seed, 'duration_seconds': float(duration),
            'buffer_capacity_waiting_frames': buffer_capacity,
            'payload_bytes': PAYLOAD_BYTES,
            'frame_wire_bytes': FRAME_WIRE_BYTES,
            'interframe_gap_byte_times': IFG_BYTES,
            'frame_occupancy_byte_times': FRAME_OCCUPANCY_BYTES,
            'transmission_seconds': tx_seconds,
            'interframe_gap_seconds': ifg_seconds,
        },
        'counts': counts,
        'timing': timing,
        'records': records,
        'records_truncated': counts['generated'] > record_limit,
    }
