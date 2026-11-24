import unittest
from simulation import run_simulation

class EngineTests(unittest.TestCase):
    def run_case(self, **kwargs):
        return run_simulation(duration=.1,base_epoch=1700000000,record_limit=None,**kwargs)
    def test_conservation_and_bounds(self):
        for load in (80,120,160):
            for split in (.5,.7,.9):
                r=self.run_case(total_load_mbps=load,traffic_split=split)
                for link in (r['link_1'],r['link_2']):
                    c,t=link['counts'],link['timing']
                    self.assertEqual(c['generated'],c['accepted']+c['dropped'])
                    self.assertEqual(c['accepted'],c['completed_total'])
                    self.assertLessEqual(link['max_queue_length'],100)
                    self.assertLessEqual(t['busy_time_observation'],.1+1e-10)
                for f in r['frame_records']:
                    self.assertLess(f['arrival_sim_time_s'],.1)
                    self.assertEqual(f['arrival_epoch_s'],1700000000+f['arrival_sim_time_s'])
                    if f['status']=='dropped':
                        self.assertEqual(f['queue_length_at_arrival'],100)
                        self.assertIsNone(f['completion_epoch_s'])
                    else:
                        self.assertGreaterEqual(f['queue_delay_s'],0)
                        self.assertAlmostEqual(f['frame_delay_s']-f['queue_delay_s'],.00012208)
    def test_reproducible(self):
        self.assertEqual(self.run_case(),self.run_case())
    def test_zero_load(self):
        self.assertEqual(self.run_case(total_load_mbps=0)['counts']['generated'],0)
    def test_record_cap(self):
        a=run_simulation(duration=.1,record_limit=0)
        b=run_simulation(duration=.1,record_limit=10)
        self.assertEqual(a['counts'],b['counts']); self.assertEqual(a['timing'],b['timing'])
        self.assertEqual(len(b['frame_records']),10)
    def test_overload(self):
        r=self.run_case(total_load_mbps=160,traffic_split=.9)
        self.assertGreater(r['link_1']['counts']['dropped'],0)
        self.assertEqual(r['link_2']['counts']['dropped'],0)
    def test_fifo(self):
        r=self.run_case(total_load_mbps=160,traffic_split=.9)
        for i in (1,2):
            frames=[f for f in r['frame_records'] if f['link_id']==i and f['status']=='delivered']
            starts=[f['tx_start_sim_time_s'] for f in frames]
            self.assertEqual(starts,sorted(starts))
            for a,b in zip(starts,starts[1:]): self.assertGreaterEqual(b-a,.00012304-1e-12)
    def test_zero_buffer(self):
        r=self.run_case(buffer_capacity=0)
        self.assertGreater(r['counts']['dropped'],0)
        self.assertEqual(r['link_1']['max_queue_length'],0)
if __name__=='__main__': unittest.main()
