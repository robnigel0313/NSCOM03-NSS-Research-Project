
import unittest

from simulation import run_simulation
from metrics import calculate_link_metrics, calculate_metrics


class MetricsTests(unittest.TestCase):

    def test_known_values(self):
        counts = {
            "generated": 1000,
            "dropped": 100,
            "completed_within_observation": 800}

        timing = {
            "delay_count_total": 900,
            "delay_sum_total": 0.9,
            "queue_delay_sum_total": 0.72,
            "busy_time_observation": 0.5}

        result = calculate_link_metrics(counts, timing, duration=1, payload_bytes=1500)

        self.assertAlmostEqual(result["throughput_mbps"], 9.6)
        self.assertAlmostEqual(result["average_delay_ms"], 1.0)
        self.assertAlmostEqual(result["frame_loss_percent"], 10.0)
        self.assertAlmostEqual(result["utilization_percent"], 50.0)
        self.assertAlmostEqual(result["average_queue_delay_ms"], 0.8)

    def test_zero_traffic(self):
        result = calculate_metrics(run_simulation(total_load_mbps=0, duration=0.1))

        for metrics in result.values():
            self.assertEqual(metrics["throughput_mbps"], 0)
            self.assertEqual(metrics["utilization_percent"], 0)
            self.assertIsNone(metrics["average_delay_ms"])
            self.assertIsNone(metrics["average_queue_delay_ms"])
            self.assertIsNone(metrics["frame_loss_percent"])

    def test_aggregate_throughput(self):
        result = calculate_metrics(run_simulation(duration=0.1))

        expected = (result["link_1"]["throughput_mbps"] + result["link_2"]["throughput_mbps"])

        self.assertAlmostEqual(result["aggregate"]["throughput_mbps"], expected)

    def test_aggregate_delay(self):
        raw = run_simulation(total_load_mbps=120, traffic_split=0.9, duration=0.1)

        result = calculate_metrics(raw)

        n1 = raw["link_1"]["timing"]["delay_count_total"]
        n2 = raw["link_2"]["timing"]["delay_count_total"]

        for metric in ("average_delay_ms", "average_queue_delay_ms"):
            d1 = result["link_1"][metric]
            d2 = result["link_2"][metric]

            expected = (d1 * n1 + d2 * n2) / (n1 + n2)

            self.assertAlmostEqual(result["aggregate"][metric], expected)

    def test_aggregate_loss(self):
        raw = run_simulation(total_load_mbps=160, traffic_split=0.9, duration=0.1)

        result = calculate_metrics(raw)

        n1 = raw["link_1"]["counts"]["generated"]
        n2 = raw["link_2"]["counts"]["generated"]

        loss1 = result["link_1"]["frame_loss_percent"]
        loss2 = result["link_2"]["frame_loss_percent"]

        expected = (loss1 * n1 + loss2 * n2) / (n1 + n2)

        self.assertAlmostEqual(result["aggregate"]["frame_loss_percent"], expected)

    def test_aggregate_utilization(self):
        result = calculate_metrics(run_simulation(duration=0.1))

        expected = (result["link_1"]["utilization_percent"] + result["link_2"]["utilization_percent"]) / 2

        self.assertAlmostEqual(result["aggregate"]["utilization_percent"], expected)

    def test_metric_bounds(self):
        result = calculate_metrics(run_simulation(total_load_mbps=160, traffic_split=0.9, duration=0.1))

        for metrics in result.values():
            self.assertGreaterEqual(metrics["throughput_mbps"], 0)
            self.assertGreaterEqual(metrics["average_delay_ms"], 0)
            self.assertGreaterEqual(metrics["average_queue_delay_ms"], 0)

            self.assertGreaterEqual(metrics["frame_loss_percent"], 0)
            self.assertLessEqual(metrics["frame_loss_percent"], 100)

            self.assertGreaterEqual(metrics["utilization_percent"], 0)
            self.assertLessEqual(metrics["utilization_percent"], 100 + 1e-8)

            self.assertGreaterEqual(metrics["average_delay_ms"], metrics["average_queue_delay_ms"])

        capacity = 100 * 1500 / 1538

        for link in ("link_1", "link_2"):
            self.assertLessEqual(result[link]["throughput_mbps"], capacity + 1e-8)

    def test_record_independence(self):
        a = calculate_metrics(run_simulation(duration=0.1, record_limit=0))

        b = calculate_metrics(run_simulation(duration=0.1, record_limit=None))

        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()