"""Actual stock wrapper and bundled CPython; explicitly standalone scope."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from protocol import sha
from validate import validate


def smoke(bundle,slot):
    bundle,slot=Path(bundle).resolve(),Path(slot).resolve()
    slot.mkdir(exist_ok=False)
    build=json.loads((bundle/'BOINC_BUILD.json').read_text())
    for name,digest in build['files'].items():
        if sha((bundle/name).read_bytes())!=digest:
            raise ValueError('Package bytes differ')
    for name in ('wrapper','runtime.zip'):
        shutil.copy2(bundle/name,slot/name)
    shutil.copy2(bundle/'controls.json',slot/'manifest.json')
    (slot/'job.xml').write_text((bundle/'job.xml').read_text().replace('</command_line>',' --standalone</command_line>'))
    env={k:v for k,v in os.environ.items() if not k.startswith(('PYTHON','DYLD_'))}
    with (slot/'wrapper.stdout').open('w') as out,(slot/'wrapper.stderr').open('w') as err:
        result=subprocess.run([str(slot/'wrapper')],cwd=slot,env=env,stdout=out,stderr=err,timeout=180)
    if result.returncode:
        for name in ('wrapper.stderr','four133.stderr'):
            if (slot/name).exists():
                print((slot/name).read_text(),file=sys.stderr)
        raise RuntimeError('Stock wrapper failed: '+str(result.returncode))
    audit=validate(slot/'manifest.json',slot/'result.json',bundle/'gmp_exact',build['engine_sha256'],'standalone')
    if audit['GMP_candidate_checks']<=0 or audit['exact_hits']:
        raise ValueError('Controls must exercise real modular matches, without an exact solution')
    audit.update(stock_wrapper_executed=True,bundled_python_executed=True,
                 actual_BOINC_client=False,cpu_budget=1,GPU=False)
    (slot/'SMOKE_ACCEPTANCE.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('bundle');p.add_argument('slot');a=p.parse_args()
    smoke(a.bundle,a.slot)
