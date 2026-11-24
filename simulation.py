"""Two independent finite-buffer Ethernet paths; SimPy event scheduler."""
import math
import random
import time
from collections import deque
from itertools import count
import simpy


def run_simulation(total_load_mbps=120, traffic_split=0.5,
                   link_capacity_mbps=100, payload_bytes=1500,
                   occupancy_byte_times=1538, buffer_capacity=100,
                   duration=60, seed=1, record_limit=10000,
                   queue_sample_interval=0.01, base_epoch=None):
    """Return raw counters, timing sums and optional records; no GUI dependency.

    record_limit=None retains all frames; 0 disables frame logging.
    queue_sample_interval=None disables periodic queue samples.
    """
    for x in (total_load_mbps, traffic_split, link_capacity_mbps, duration):
        if not math.isfinite(x):
            raise ValueError('Inputs must be finite')
    if total_load_mbps < 0 or not 0 <= traffic_split <= 1 or link_capacity_mbps <= 0 or duration <= 0:
        raise ValueError('Invalid load, split, capacity or duration')
    if not isinstance(payload_bytes, int) or payload_bytes <= 0 or occupancy_byte_times < payload_bytes + 12:
        raise ValueError('Invalid frame size')
    if not isinstance(buffer_capacity, int) or buffer_capacity < 0:
        raise ValueError('Invalid waiting capacity')
    if record_limit is not None and (not isinstance(record_limit, int) or record_limit < 0):
        raise ValueError('Invalid record limit')
    if queue_sample_interval is not None and (not math.isfinite(queue_sample_interval) or queue_sample_interval <= 0):
        raise ValueError('Invalid sampling interval')
    base = time.time() if base_epoch is None else float(base_epoch)
    if not math.isfinite(base):
        raise ValueError('Invalid epoch')
    env = simpy.Environment()
    service = occupancy_byte_times * 8 / (link_capacity_mbps * 1e6)
    delivery = (occupancy_byte_times - 12) * 8 / (link_capacity_mbps * 1e6)
    records, samples = [], []
    ids = count(1)
    scenario = f'{total_load_mbps:g}Mbps_{traffic_split:g}'
    run_id = f'{scenario}_{seed}_{base:.9f}'
    config = dict(total_load_mbps=total_load_mbps, traffic_split=traffic_split,
                  link_capacity_mbps=link_capacity_mbps, payload_bytes=payload_bytes,
                  occupancy_byte_times=occupancy_byte_times, buffer_capacity=buffer_capacity,
                  duration_seconds=duration, seed=seed, service_time_s=service,
                  transmission_time_s=delivery, scenario_id=scenario)

    class Link:
        def __init__(self, number, load):
            self.number, self.load = number, load
            self.rng = random.Random(f'{seed}:link:{number}')
            self.waiting = deque()
            self.busy = False
            self.c = dict.fromkeys(('generated','accepted','dropped','completed_within_observation','completed_total'), 0)
            self.t = dict.fromkeys(('busy_time_observation','delay_sum_total','delay_count_total','delay_sum_observation','delay_count_observation','queue_delay_sum_total'), 0)
            self.max_queue = 0

        def arrivals(self):
            rate = self.load * 1e6 / (payload_bytes * 8)
            if not rate:
                return
            while True:
                gap = self.rng.expovariate(rate)
                if env.now + gap >= duration:
                    return
                yield env.timeout(gap)
                self.admit()

        def admit(self):
            now = env.now
            fid = next(ids)
            self.c['generated'] += 1
            drop = self.busy and len(self.waiting) >= buffer_capacity
            rec = None
            if record_limit is None or len(records) < record_limit:
                rec = dict(run_id=run_id, scenario_id=scenario, seed=seed, frame_id=fid,
                           link_id=self.number, payload_bytes=payload_bytes,
                           arrival_sim_time_s=now, arrival_epoch_s=base+now,
                           tx_start_sim_time_s=None, tx_start_epoch_s=None,
                           completion_sim_time_s=None, completion_epoch_s=None,
                           queue_delay_s=None, frame_delay_s=None,
                           queue_length_at_arrival=len(self.waiting),
                           status='dropped' if drop else 'accepted',
                           drop_reason='buffer_full' if drop else None,
                           completed_within_observation=False)
                records.append(rec)
            if drop:
                self.c['dropped'] += 1
                return
            self.c['accepted'] += 1
            frame = (now, rec)
            if self.busy:
                self.waiting.append(frame)
                self.max_queue = max(self.max_queue, len(self.waiting))
            else:
                self.busy = True
                env.process(self.transmit(frame))

        def transmit(self, frame):
            while True:
                arrival, rec = frame
                start = env.now
                self.t['busy_time_observation'] += max(0, min(duration-start, service))
                yield env.timeout(delivery)
                end = env.now
                delay = end-arrival
                within = end <= duration
                self.c['completed_total'] += 1
                self.t['delay_sum_total'] += delay
                self.t['delay_count_total'] += 1
                self.t['queue_delay_sum_total'] += start-arrival
                if within:
                    self.c['completed_within_observation'] += 1
                    self.t['delay_sum_observation'] += delay
                    self.t['delay_count_observation'] += 1
                if rec is not None:
                    rec.update(tx_start_sim_time_s=start, tx_start_epoch_s=base+start,
                               completion_sim_time_s=end, completion_epoch_s=base+end,
                               queue_delay_s=start-arrival, frame_delay_s=delay,
                               status='delivered', completed_within_observation=within)
                yield env.timeout(service-delivery)
                if not self.waiting:
                    self.busy = False
                    return
                frame = self.waiting.popleft()

        def result(self):
            c = self.c
            c['completed_during_drain'] = c['completed_total']-c['completed_within_observation']
            c['unfinished_at_observation'] = c['accepted']-c['completed_within_observation']
            return dict(link_id=self.number, offered_load_mbps=self.load, counts=c,
                        timing=self.t, max_queue_length=self.max_queue)

    links = [Link(1,total_load_mbps*traffic_split), Link(2,total_load_mbps*(1-traffic_split))]
    for link in links:
        env.process(link.arrivals())
    def sample():
        i = 0
        while i*queue_sample_interval < duration:
            target = i*queue_sample_interval
            if target > env.now:
                yield env.timeout(target-env.now)
            for link in links:
                samples.append(dict(sim_time_s=env.now, link_id=link.number,
                                    waiting_frames=len(link.waiting), busy=link.busy))
            i += 1
    if queue_sample_interval is not None:
        env.process(sample())
    env.run(until=duration)
    env.run()
    a,b = [link.result() for link in links]
    counts = {k:a['counts'][k]+b['counts'][k] for k in a['counts']}
    timing = {k:a['timing'][k]+b['timing'][k] for k in a['timing']}
    timing['end_time'] = env.now
    return dict(config=config, run_id=run_id, base_epoch=base,
                observation_duration=duration, drain_duration=max(0,env.now-duration),
                link_1=a, link_2=b, counts=counts, timing=timing,
                frame_records=records, queue_records=samples,
                records_truncated=counts['generated']>len(records))
