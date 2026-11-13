#!/usr/bin/env python3
"""Register exact trusted input/version, then submit with stock create_work."""
import argparse,hashlib,json,re,shlex,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--stock',required=True);p.add_argument('--runtime',required=True);p.add_argument('--manifest',required=True);p.add_argument('--name',required=True);p.add_argument('--app-version-id',type=int,required=True);p.add_argument('--build',choices=['A','B'],required=True);p.add_argument('--command-line',default='');p.add_argument('--backend',choices=['cpu','gpu'],default='cpu');a=p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_-]+',a.name):raise ValueError('Unsafe logical job name')
s=Path(a.stock).resolve();runtime=Path(a.runtime).resolve();app=Path(__file__).resolve().parents[1]/'app';project=s/'project'
manifest=Path(a.manifest).read_bytes();m=json.loads(manifest)
if m.get('TEST_ONLY') is not True or m.get('new_scientific_coverage') is not False:raise ValueError('Only TEST_ONLY fixtures allowed')
mysql=[str(s/'root/usr/bin/mariadb'),'--no-defaults','--protocol=TCP','-h127.0.0.1','-uroot']
def sql(q):return subprocess.check_output(mysql+['--batch','--skip-column-names','fifth42','-e',q],text=True).strip()
if sql(f"SELECT id FROM workunit WHERE name='{a.name}'"):raise ValueError('Workunit already exists; no duplicate submission')
rows=sql(f"SELECT av.version_num FROM app_version av JOIN app ON app.id=av.appid WHERE av.id={a.app_version_id} AND app.name='fifth42'")
if not rows or not rows.isdecimal():raise ValueError('Unknown or ambiguous registered BOINC app version')
trusted=s/'trusted';trusted.mkdir(exist_ok=True);dest=trusted/(a.name+'.json')
if dest.exists():raise ValueError('Trusted manifest already exists; inspect previous attempt before retry')
dest.write_bytes(manifest)
cpath=s/'validator-config.json'
cfg=json.loads(cpath.read_text()) if cpath.exists() else dict(mysql_command=mysql,database='fifth42',gmp_reference=str(runtime/'bin/gmp_reference'),audit_directory=str(s/'validator-audit'),workunits={},application_versions={})
cfg['workunits'][a.name]=dict(manifest=str(dest),allowed_app_version_ids=[a.app_version_id])
engine='scaling_gpu' if a.backend=='gpu' else 'scaling_cpu'
b=dict(engine_sha256=hashlib.sha256((runtime/'bin'/engine).read_bytes()).hexdigest(),build=a.build,backend='gpu' if a.backend=='gpu' else 'emulated')
prior=cfg['application_versions'].get(str(a.app_version_id))
if prior is not None and dict(prior,backend=prior.get('backend','emulated'))!=b:raise ValueError('Cannot change an immutable app version identity')
cfg['application_versions'][str(a.app_version_id)]=b
(s/'validator-audit').mkdir(exist_ok=True)
tmp=cpath.with_suffix('.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\n');tmp.replace(cpath)
hook=project/'bin/fifth42_validate'
hook.write_text('#!/bin/bash\nexport PYTHONPATH='+shlex.quote(str(app)+':'+str(runtime))+'\nexport FIFTH42_VALIDATOR_CONFIG='+shlex.quote(str(cpath))+'\nexec /usr/bin/python3 '+shlex.quote(str(app/'boinc_validate.py'))+' "$@"\n');hook.chmod(0o755)
subprocess.run(['bin/stage_file_native','--copy',str(dest)],cwd=project,check=True)
subprocess.run(['bin/create_work','--appname','fifth42','--wu_name',a.name,'--app_version_num',rows,'--wu_template','templates/fifth42_in','--result_template','templates/fifth42_out','--command_line',('--passthrough_child '+a.command_line) if a.command_line else '',dest.name],cwd=project,check=True)
print(json.dumps(dict(name=a.name,app_version_id=a.app_version_id,version_num=int(rows),TEST_ONLY=True,new_scientific_coverage=False)))
