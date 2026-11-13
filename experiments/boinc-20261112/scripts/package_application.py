#!/usr/bin/env python3
"""Create immutable CPU application contents; BOINC stages/signs/distributes them."""
import argparse,hashlib,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--destination',required=True);p.add_argument('--build',choices=['A','B'],required=True);p.add_argument('--backend',choices=['cpu','gpu'],default='cpu');a=p.parse_args()
r=Path(a.runtime);d=Path(a.destination);d.mkdir(parents=True,exist_ok=False)
app=Path(__file__).resolve().parents[1]/'app'
s=(app/'science_driver.py').read_text().replace('APPLICATION_BUILD="prototype-dev"',f'APPLICATION_BUILD="{a.build}"')
(d/'science_driver.py').write_text(s)
for name in ['engine_session.py','colab_bench.py']:shutil.copy2(r/name,d/name)
engine='scaling_gpu' if a.backend=='gpu' else 'scaling_cpu'
shutil.copy2(r/'bin'/engine,d/engine)
files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in d.iterdir()}
(d/'BUILD.json').write_text(json.dumps(dict(build=a.build,backend=a.backend,source_commit='4668a27951f2b9d7d533896d1aa32684808341d4',TEST_ONLY=True,files=files),sort_keys=True,indent=2)+'\n')
print(json.dumps(files,sort_keys=True))
