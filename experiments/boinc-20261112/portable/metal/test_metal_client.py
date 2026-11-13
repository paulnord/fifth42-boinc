"""Direct GPU controls on an explicitly selected Metal device; no CPU fallback."""
import argparse,json,subprocess,sys
from pathlib import Path
base=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--device-registry-id');p.add_argument('--list-devices',action='store_true');p.add_argument('--destination');a=p.parse_args()
engine=base/'bin/scaling_gpu'
if a.list_devices:
    subprocess.run([str(engine),'--list-devices'],check=True);raise SystemExit(0)
if not a.device_registry_id or not a.destination:p.error('Select --device-registry-id from --list-devices and a fresh --destination')
dest=Path(a.destination).resolve();dest.mkdir(exist_ok=False)
subprocess.run([sys.executable,str(base/'app/science_driver.py'),'--manifest',str(base/'controls.json'),
    '--engine',str(engine),'--build','A','--backend','metal','--metal-device-registry-id',a.device_registry_id],cwd=dest,check=True,timeout=120)
r=json.loads((dest/'result.json').read_text())
assert r['TEST_ONLY'] is True and r['new_scientific_coverage'] is False and r['backend']=='gpu'
assert r['metal_device_registry_id']==a.device_registry_id and r['completed_prefix']==3
assert sum(x['response']['points_visited'] for x in r['receipts'])==9
print('PASS: Metal GPU application, 3 controls, 9 positions; zero production coverage')
