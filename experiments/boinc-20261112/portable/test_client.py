#!/usr/bin/env python3
"""Run the built CPU application directly on known TEST_ONLY controls."""
import argparse,json,os,subprocess,sys
from pathlib import Path
base=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--destination',required=True);a=p.parse_args()
dest=Path(a.destination).resolve();dest.mkdir(exist_ok=False)
engine=base/'bin'/('scaling_cpu.exe' if os.name=='nt' else 'scaling_cpu')
cmd=[sys.executable,str(base/'app/science_driver.py'),'--manifest',str(base/'controls.json'),'--engine',str(engine),'--build','A']
subprocess.run(cmd,cwd=dest,check=True,timeout=60)
result=json.loads((dest/'result.json').read_text())
assert result['TEST_ONLY'] is True and result['new_scientific_coverage'] is False
assert result['completed_prefix']==3 and sum(x['response']['points_visited'] for x in result['receipts'])==9
print('PASS: native CPU application, 3 control packets, 9 positions; zero production coverage')
