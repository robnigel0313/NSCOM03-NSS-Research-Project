
import unittest

from report_generator import (
    classify_difference,
    classify_impact,
    identify_metric,
    calculate_effective_capacity,
    classify_capacity,
    interpret_metric,
    interpret_configuration,
    interpret_link_capacity,
    interpret_bottleneck)


class TestStatisticalClassification(unittest.TestCase):

    def test_increase(self):
        self.assertEqual(classify_difference(5, 3, 7), "increase")

    def test_decrease(self):
        self.assertEqual(classify_difference(-5, -7, -3), "decrease")

    def test_inconclusive(self):
        self.assertEqual(classify_difference(1, -2, 4), "inconclusive")

    def test_interval_touches_zero(self):
        self.assertEqual(classify_difference(2, 0, 4), "inconclusive")

    def test_no_observed_difference(self):
        self.assertEqual(classify_difference(0, 0, 0), "no_observed_difference")

    def test_unavailable(self):
        self.assertEqual(classify_difference(None, None, None), "unavailable")

    def test_nonfinite(self):
        self.assertEqual(classify_difference(float("nan"), 0, 1), "unavailable")

    def test_invalid_interval(self):
        self.assertEqual(classify_difference(5, 7, 3), "invalid")

    def test_mean_outside_interval(self):
        self.assertEqual(classify_difference(10, 3, 7), "invalid")


class TestPerformanceImpact(unittest.TestCase):

    def test_higher_is_better(self):
        self.assertEqual(classify_impact("increase", "higher"), "improvement")

        self.assertEqual(classify_impact("decrease", "higher"), "degradation")

    def test_lower_is_better(self):
        self.assertEqual(classify_impact("decrease", "lower"), "improvement")

        self.assertEqual(classify_impact("increase", "lower"), "degradation")

    def test_context_dependent(self):
        self.assertEqual(classify_impact("increase", "context"), "context_dependent")

        self.assertEqual(classify_impact("decrease", "context"), "context_dependent")

    def test_inconclusive_impact(self):
        self.assertEqual(classify_impact("inconclusive", "higher"), "inconclusive")

    def test_individual_link_throughput(self):
        properties = identify_metric( "link_1_throughput_mbps")

        self.assertEqual(properties["preferred"], "context")

    def test_aggregate_throughput(self):
        properties = identify_metric( "aggregate_throughput_mbps")

        self.assertEqual(properties["preferred"], "higher")



class TestConfigurationInterpretation(unittest.TestCase):

    def get_categories(self, throughput, delay, loss, loss_mean=0):
        metrics = {"aggregate_throughput_mbps": (throughput, "higher"),
            "aggregate_average_delay_ms": (delay, "lower"), 
            "aggregate_frame_loss_percent": (loss, "lower")}

        comparisons = {
            metric: {"direction": direction, "impact": classify_impact(direction, preferred)} for metric, (direction, preferred) in metrics.items()}

        summary = {"aggregate_frame_loss_percent": {"mean": loss_mean}}

        findings = interpret_configuration(summary, comparisons)

        return {finding["category"] for finding in findings}

    def test_delivery_degradation(self):
        categories = self.get_categories("decrease", "increase", "increase", 10)

        self.assertIn("delivery_degradation", categories)

        self.assertIn("performance_degradation", categories)

        self.assertIn("observed_loss", categories)

    def test_latency_without_loss(self):
        categories = self.get_categories("inconclusive", "increase", "no_observed_difference")

        self.assertIn("latency_without_loss", categories)

        self.assertIn("latency_without_throughput_degradation", categories)

    def test_performance_improvement(self):
        categories = self.get_categories("increase", "decrease", "decrease", 1)

        self.assertIn("performance_improvement", categories)

    def test_performance_tradeoff(self):
        categories = self.get_categories("increase", "increase", "inconclusive", 1)

        self.assertIn("performance_tradeoff", categories)

    def test_no_observed_difference(self):
        categories = self.get_categories("no_observed_difference",
            "no_observed_difference",
            "no_observed_difference")

        self.assertIn("no_observed_difference", categories)

    def test_inconclusive_performance(self):
        categories = self.get_categories("inconclusive", "inconclusive", "inconclusive", 1)

        self.assertIn("inconclusive_performance_change", categories)

    def test_incomplete_assessment(self):
        categories = self.get_categories("unavailable", "inconclusive", "invalid", None)

        self.assertIn("incomplete_assessment", categories)

        self.assertIn("loss_unavailable", categories)



class TestCapacityInterpretation(unittest.TestCase):

    def setUp(self):
        self.capacity = calculate_effective_capacity(
            100, 1500, 1538
        )

    def test_effective_capacity(self):
        self.assertAlmostEqual(
            self.capacity, 97.52925877763329
        )

    def test_invalid_capacity_parameters(self):
        with self.assertRaises(ValueError):
            calculate_effective_capacity(
                100, 1500, 1000
            )

    def test_capacity_conditions(self):
        cases = [
            (0, "no_traffic"),
            (72, "below_capacity"),
            (self.capacity, "at_capacity"),
            (108, "above_capacity"),
            (None, "unavailable"),
            (-10, "unavailable")
        ]

        for load, expected in cases:
            with self.subTest(load=load):
                self.assertEqual(
                    classify_capacity(
                        load, self.capacity
                    ),
                    expected
                )

    def get_bottleneck(self, load_1, load_2):
        link_1 = interpret_link_capacity(
            load_1, self.capacity, None, None, None
        )

        link_2 = interpret_link_capacity(
            load_2, self.capacity, None, None, None
        )

        return interpret_bottleneck(
            link_1, link_2
        )["category"]

    def test_no_overload(self):
        self.assertEqual(
            self.get_bottleneck(40, 40),
            "no_theoretical_overload"
        )

    def test_imbalance_bottleneck(self):
        self.assertEqual(
            self.get_bottleneck(108, 12),
            "imbalance_bottleneck"
        )

    def test_second_link_overloaded(self):
        self.assertEqual(
            self.get_bottleneck(12, 108),
            "imbalance_bottleneck"
        )

    def test_both_links_overloaded(self):
        self.assertEqual(
            self.get_bottleneck(120, 120),
            "both_links_overloaded"
        )

    def test_capacity_bottleneck(self):
        self.assertEqual(
            self.get_bottleneck(150, 80),
            "capacity_bottleneck"
        )

    def test_capacity_limit(self):
        self.assertEqual(
            self.get_bottleneck(self.capacity, 40),
            "capacity_limit"
        )

    def test_no_traffic(self):
        self.assertEqual(
            self.get_bottleneck(0, 0),
            "no_traffic"
        )

    def test_unavailable_capacity(self):
        self.assertEqual(
            self.get_bottleneck(None, 40),
            "unavailable"
        )

    def test_loss_below_capacity(self):
        result = interpret_link_capacity(
            80, self.capacity, 82, 1000, 5
        )

        self.assertTrue(
            any(
                "temporary buffer overflow" in finding
                for finding in result["findings"]
            )
        )


if __name__ == "__main__":
    unittest.main()
