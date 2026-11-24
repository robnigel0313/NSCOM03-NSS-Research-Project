"""Official experimental settings."""
LOADS = (80, 120, 160)
SPLITS = (0.5, 0.7, 0.9)
SEEDS = tuple(range(1, 11))
DEFAULTS = dict(link_capacity_mbps=100, payload_bytes=1500,
                occupancy_byte_times=1538, buffer_capacity=100, duration=60)
