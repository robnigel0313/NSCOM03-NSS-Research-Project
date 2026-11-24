import argparse, csv, json
from pathlib import Path
from simulation import run_simulation

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--load',type=float,default=120)
    p.add_argument('--split',type=float,default=0.9)
    p.add_argument('--duration',type=float,default=60)
    p.add_argument('--seed',type=int,default=1)
    p.add_argument('--all-frames',action='store_true')
    p.add_argument('--output',default='samples/run')
    a=p.parse_args()
    r=run_simulation(a.load,a.split,duration=a.duration,seed=a.seed,record_limit=None if a.all_frames else 10000)
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    for key in ('frame_records','queue_records'):
        rows=r.pop(key)
        if rows:
            with (out/f'{key}.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (out/'run_summary.json').write_text(json.dumps(r,indent=2))
    print(json.dumps({k:r[k] for k in ('link_1','link_2','counts')},indent=2))
if __name__=='__main__': main()
