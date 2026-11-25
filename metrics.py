
def calculate_link_metrics(counts, timing, duration, payload_bytes, num_links=1):
    generated = counts["generated"]
    dropped = counts["dropped"]
    completed = counts["completed_within_observation"]

    delay_count = timing["delay_count_total"]
    delay_sum = timing["delay_sum_total"]
    queue_delay_sum = timing["queue_delay_sum_total"]
    busy_time = timing["busy_time_observation"]

    #payload throughput (Mbps)
    throughput = (completed * payload_bytes * 8) / (duration * 1e6)

    #ave frame delay (ms)
    average_delay = ((delay_sum / delay_count) * 1000
        if delay_count > 0 else None)

    #frame loss (%)
    frame_loss = ((dropped / generated) * 100
        if generated > 0 else None)

    #link utilization (%)
    utilization = (busy_time / (num_links * duration)) * 100

    #ave queueing delay (ms)
    average_queue_delay = ((queue_delay_sum / delay_count) * 1000
        if delay_count > 0 else None)

    return {
        "throughput_mbps": throughput,
        "average_delay_ms": average_delay,
        "frame_loss_percent": frame_loss,
        "utilization_percent": utilization,
        "average_queue_delay_ms": average_queue_delay}


def calculate_metrics(simulation_result):
    duration = simulation_result["observation_duration"]
    payload_bytes = simulation_result["config"]["payload_bytes"]

    link_1 = simulation_result["link_1"]
    link_2 = simulation_result["link_2"]

    return {
        "link_1": calculate_link_metrics(
            link_1["counts"],
            link_1["timing"],
            duration,
            payload_bytes),
        "link_2": calculate_link_metrics(
            link_2["counts"],
            link_2["timing"],
            duration,
            payload_bytes),
        "aggregate": calculate_link_metrics(
            simulation_result["counts"],
            simulation_result["timing"],
            duration,
            payload_bytes,
            num_links=2)}
