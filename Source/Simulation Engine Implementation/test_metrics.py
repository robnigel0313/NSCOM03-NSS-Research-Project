from simulation import run_simulation
from metrics import calculate_metrics

# zero, normal, and overloaded traffic
test_scenarios = [0, 50, 200]

for offered_load in test_scenarios:
    results = run_simulation(link_speed=100, offered_load=offered_load, seed=42, duration=1)
    metrics = calculate_metrics(results)

    print("\n===== ETHERNET SIMULATION RESULTS =====")
    print(f"Link Speed:          {results['config']['link_speed_mbps']} Mbps")
    print(f"Offered Load:        {results['config']['offered_load_mbps']} Mbps")
    print("---------------------------------------")

    print(f"Payload Throughput:  {metrics['throughput_mbps']:.2f} Mbps")

    delay = metrics['average_delay_ms']
    print(f"Average Frame Delay: {delay:.2f} ms" if delay is not None
        else "Average Frame Delay: N/A")

    print(f"Frame Loss:          {metrics['frame_loss_percent']:.2f}%")
    print(f"Link Utilization:    {metrics['utilization_percent']:.2f}%")
    print("=======================================\n")