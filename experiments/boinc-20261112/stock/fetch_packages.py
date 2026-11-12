#!/usr/bin/env python3
"""Extract the exact official Debian packages used, without root or postinst scripts."""
import argparse,hashlib,json,subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('destination');p.add_argument('--jobs',type=int,default=8);a=p.parse_args()
r=Path(a.destination).resolve();(r/'debs').mkdir(parents=True,exist_ok=True);(r/'root').mkdir(exist_ok=True)
lock=json.loads(Path(__file__).with_name('debian13-amd64-packages.lock.json').read_text())
def fetch(d):
 dest=r/'debs'/Path(d['Filename']).name
 if not dest.exists():
  tmp=dest.with_suffix('.part')
  subprocess.run(['curl','--fail','--location','--retry','2','https://deb.debian.org/debian/'+d['Filename'],'-o',str(tmp)],check=True);tmp.rename(dest)
 if hashlib.sha256(dest.read_bytes()).hexdigest()!=d['SHA256']:raise ValueError('Package digest mismatch: '+d['Package'])
 return dest
with ThreadPoolExecutor(max_workers=a.jobs) as pool:
 files=list(pool.map(fetch,lock))
# Finish every download before extraction; no concurrent writers while building.
for f in files:subprocess.run(['dpkg-deb','--extract',str(f),str(r/'root')],check=True)
(r/'packages-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
