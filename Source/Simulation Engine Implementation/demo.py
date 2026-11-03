"""Small stand-alone smoke demo for the Ethernet simulation engine."""
from simulation import run_simulation

if __name__ == '__main__':
    for speed in (10, 100, 1000):
        result = run_simulation(speed, 50, seed=42, duration=0.5, record_limit=5)
        print(f'\n{speed} Mbps | offered load 50 Mbps')
        print('Counts:', result['counts'])
        print('Timing:', result['timing'])
        print('Sample records:', result['records'][:2])
