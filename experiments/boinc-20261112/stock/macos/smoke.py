"""Execute the actual stock wrapper, unzip and bundled runtime in a fresh slot."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('bundle');p.add_argument('slot');a=p.parse_args()
base=Path(a.bundle).resolve();slot=Path(a.slot).resolve();slot.mkdir(exist_ok=False)
metadata=json.loads((base/'BOINC_BUILD.json').read_text())
for name,digest in metadata['files'].items():assert hashlib.sha256((base/name).read_bytes()).hexdigest()==digest,name
for name in ('wrapper','runtime.zip','job.xml'):shutil.copy2(base/name,slot/name)
shutil.copy2(base/'controls.json',slot/'manifest.json')
environment={k:v for k,v in os.environ.items() if not k.startswith(('PYTHON','DYLD_'))}
with (slot/'wrapper.stdout').open('w') as out,(slot/'wrapper.stderr').open('w') as err:
    run=subprocess.run([str(slot/'wrapper')],cwd=slot,env=environment,stdout=out,stderr=err,timeout=120)
if run.returncode:
    for name in ('wrapper.stderr','science.stderr'):
        if (slot/name).exists():print((slot/name).read_text(),file=sys.stderr)
    raise RuntimeError('Stock wrapper smoke failed: '+str(run.returncode))
r=json.loads((slot/'result.json').read_text())
assert r['TEST_ONLY'] is True and r['new_scientific_coverage'] is False
assert r['engine_sha256']==metadata['engine_sha256'] and r['completed_prefix']==3
assert sum(receipt['response']['points_visited'] for receipt in r['receipts'])==9
identity=subprocess.check_output([str(slot/'python/bin/python3.13'),'-c','import platform,sys;print(platform.machine(),sys.version)'],env=environment,text=True)
report=dict(stock_wrapper_executed=True,bundled_python_executed=True,cpu_engine_executed=True,packets=3,positions=9,
    runtime=identity.strip(),engine_sha256=r['engine_sha256'],TEST_ONLY=True,new_scientific_coverage=False)
(base/'WRAPPER_SMOKE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
