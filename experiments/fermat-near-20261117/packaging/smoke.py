"""Execute the stock CPU wrapper and bundled runtime without a BOINC client."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from make_work import make
from protocol import atomic,sha
from validate import validate


def smoke(bundle,slot,oracle):
    bundle,slot=Path(bundle).resolve(),Path(slot).resolve()
    build=json.loads((bundle/'BOINC_BUILD.json').read_text())
    if build['backend']!='cpu':raise ValueError('This smoke test selects the CPU package')
    slot.mkdir(exist_ok=False)
    for name in build['client_files']:
        if sha((bundle/name).read_bytes())!=build['files'][name]:raise ValueError('Package bytes changed')
        shutil.copy2(bundle/name,slot/name)
    job=(slot/'job.xml').read_text().replace('</command_line>',' --standalone</command_line>')
    (slot/'job.xml').write_text(job)
    atomic(slot/'manifest.json',make('wrapper-controls',list(range(4,33)),2,40,rows=256))
    env={k:v for k,v in os.environ.items() if not k.startswith(('PYTHON','DYLD_'))}
    if sys.platform.startswith('linux'):env['LD_LIBRARY_PATH']=str(slot)+':'+env.get('LD_LIBRARY_PATH','')
    with (slot/'wrapper.stdout').open('w') as out,(slot/'wrapper.stderr').open('w') as err:
        result=subprocess.run([str(slot/'wrapper')],cwd=slot,env=env,stdout=out,stderr=err,timeout=180)
    if result.returncode:raise RuntimeError('Stock wrapper failed: '+str(result.returncode))
    audit=validate(slot/'manifest.json',slot/'result.json',str(Path(oracle).resolve()),
                   build['build_identity'],'cpu','standalone')
    audit.update(stock_wrapper_executed=True,bundled_python_executed=True,actual_BOINC_client=False)
    atomic(slot/'SMOKE_ACCEPTANCE.json',audit)
    print(json.dumps(audit,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('bundle');p.add_argument('slot');p.add_argument('--oracle',required=True)
    a=p.parse_args();smoke(a.bundle,a.slot,a.oracle)
