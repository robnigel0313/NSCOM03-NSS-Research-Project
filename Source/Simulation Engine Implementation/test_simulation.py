"""Run with: python -m unittest discover -s tests -v"""
import math
import unittest
from simulation import run_simulation, FRAME_OCCUPANCY_BYTES, FRAME_WIRE_BYTES


class TestSimulation(unittest.TestCase):
    def test_zero_traffic(self):
        r = run_simulation(100, 0, seed=3, duration=1)
        self.assertEqual(r['counts']['generated'], 0)
        self.assertEqual(r['counts']['completed_total'], 0)
        self.assertEqual(r['timing']['busy_time_observation'], 0)
        self.assertAlmostEqual(r['timing']['end_time'], 1)

    def test_reproducible(self):
        self.assertEqual(run_simulation(100, 5, seed=19, duration=.2),
                         run_simulation(100, 5, seed=19, duration=.2))

    def test_accounting_and_buffer(self):
        r = run_simulation(10, 200, seed=7, duration=.2, buffer_capacity=100)
        c = r['counts']
        self.assertGreater(c['dropped'], 0)
        self.assertEqual(c['generated'], c['accepted'] + c['dropped'])
        self.assertEqual(c['accepted'], c['completed_total'])
        self.assertEqual(c['unfinished_at_observation'], c['completed_during_drain'])
        self.assertLessEqual(r['timing']['busy_time_observation'], .2 + 1e-9)

    def test_zero_waiting_buffer(self):
        r = run_simulation(10, 100, seed=1, duration=.1, buffer_capacity=0)
        self.assertGreater(r['counts']['dropped'], 0)
        self.assertGreater(r['counts']['completed_total'], 0)

    def test_light_traffic_delay_and_wire_size(self):
        r = run_simulation(1000, 0.01, seed=4, duration=10)
        self.assertEqual(r['config']['frame_wire_bytes'], 1526)
        self.assertEqual(FRAME_OCCUPANCY_BYTES, 1538)
        self.assertGreater(r['counts']['completed_total'], 0)
        for row in r['records']:
            if row['status'] == 'delivered':
                self.assertGreaterEqual(row['completion_time'] - row['arrival_time'] + 1e-12,
                                        FRAME_WIRE_BYTES * 8 / 1e9)

    def test_record_cap_does_not_affect_totals(self):
        a = run_simulation(10, 50, seed=8, duration=.1, record_limit=0)
        b = run_simulation(10, 50, seed=8, duration=.1, record_limit=30)
        self.assertEqual(a['counts'], b['counts'])
        self.assertEqual(a['timing'], b['timing'])
        self.assertEqual(a['records'], [])
        self.assertLessEqual(len(b['records']), 30)

    def test_invalid_inputs(self):
        for kwargs in [dict(link_speed=42, offered_load=1),
                       dict(link_speed=10, offered_load=-1),
                       dict(link_speed=10, offered_load=float('nan')),
                       dict(link_speed=10, offered_load=1, duration=0),
                       dict(link_speed=10, offered_load=1, buffer_capacity=-1)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_simulation(**kwargs)


if __name__ == '__main__':
    unittest.main()
