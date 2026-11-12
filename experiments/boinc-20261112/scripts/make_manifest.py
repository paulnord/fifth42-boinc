#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
CATALOG='3916c409f159cace521d9fdc24534dfadb61b514a33ada1eaf5f42e1b3203a92'
p=argparse.ArgumentParser();p.add_argument('--catalog',required=True);p.add_argument('--output',required=True);p.add_argument('--names',nargs='+',required=True);a=p.parse_args()
raw=Path(a.catalog).read_bytes()
if hashlib.sha256(raw).hexdigest()!=CATALOG: raise ValueError('Catalog identity differs')
rows={r['name']:r for r in map(json.loads,raw.splitlines())}
if len(set(a.names))!=len(a.names): raise ValueError('Duplicate packet')
m=dict(schema='fifth42-boinc-test-v1',TEST_ONLY=True,new_scientific_coverage=False,catalog_sha256=CATALOG,native_source_commit='4668a27951f2b9d7d533896d1aa32684808341d4',packets=[rows[n] for n in a.names])
Path(a.output).write_text(json.dumps(m,sort_keys=True,indent=2)+'\n')
