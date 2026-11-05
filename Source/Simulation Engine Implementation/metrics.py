# throughput = (delivered_frames * payload_bytes * 8) / (duration * 1000000)
def calculate_payload_throughput(delivered_frames, payload_bytes, duration):
    payload_throughput = (delivered_frames * payload_bytes * 8) / (duration * 1e6)
    return payload_throughput

# average delay = (delay of successful delivered frames / successful delivered frames) * 1000ms
def calculate_average_delay(delay_sum, delay_count):
    if delay_count == 0:
        return None

    average_delay = (delay_sum / delay_count) * 1000
    return average_delay

# frame loss = (number of dropped frames / total generated frames) * 100
def calculate_frame_loss(dropped_frames, generated_frames):
    if generated_frames == 0:
        return 0.0

    frame_loss = (dropped_frames / generated_frames) * 100
    return frame_loss

# link utilization = total link occupied time / total observation time * 100
def calculate_utilization(busy_time, duration):
    utilization = (busy_time / duration) * 100
    return utilization


def calculate_metrics(simulation_results):
    config = simulation_results['config']
    counts = simulation_results['counts']
    timing = simulation_results['timing']

    # values for payload throughput
    delivered_frames = counts['completed_within_observation']
    payload_bytes = config['payload_bytes']
    duration = config['duration_seconds']

    # values for average frame delay
    delay_sum = timing['delay_sum_total']
    delay_count = timing['delay_count_total']

    # values for frame loss
    dropped_frames = counts['dropped']
    generated_frames = counts['generated']

    # values for link utilization
    busy_time = timing['busy_time_observation']

    throughput = calculate_payload_throughput(delivered_frames, payload_bytes, duration)

    average_delay = calculate_average_delay(delay_sum, delay_count)

    frame_loss = calculate_frame_loss(dropped_frames, generated_frames)

    utilization = calculate_utilization(busy_time, duration)

    # calculated metrics
    return {
        'throughput_mbps': throughput,
        'average_delay_ms': average_delay,
        'frame_loss_percent': frame_loss,
        'utilization_percent': utilization
    }