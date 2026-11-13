import hashlib,json,os,shutil,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
s=Path(os.environ['STOCK']); runtime=Path(os.environ['RUNTIME']); e=Path('/evidence')
# The client's attach argv contains a local account key. Keep raw ps evidence
# private beside its state; the portable evidence contains a redacted copy.
processes=e/'processes-during.txt'
if processes.exists():
    raw=processes.read_text()
    (s/'processes-during-private.txt').write_text(raw)
    key=(s/'account-key').read_text().strip()
    processes.write_text(raw.replace(key,'<REDACTED_ACCOUNT_KEY>'))
mysql=[str(s/'root/usr/bin/mariadb'),'--no-defaults','--protocol=TCP','-h127.0.0.1','-uroot','--batch','fifth42','-e']
for table in ('result','workunit','app_version'):
    text=subprocess.check_output(mysql+[f'SELECT * FROM {table} ORDER BY id'],text=True)
    (e/f'server-{table}.tsv').write_text(text)
shutil.copy2(s/'cabbage-control.json',e/'control-manifest.json')
shutil.copytree(s/'validator-audit',e/'validator-audit',dirs_exist_ok=True)
uploaded=e/'uploaded';uploaded.mkdir(exist_ok=True)
for p in (s/'validator-audit').glob('*.json'):
    a=json.loads(p.read_text())
    shutil.copy2(Path(a['uploaded_output']),uploaded/Path(a['uploaded_output']).name)
version=s/'project/apps/fifth42/1.00/x86_64-pc-linux-gnu'
projects=list((s/'client/projects').iterdir())
assert len(projects)==1,projects
hashes=[]
for f in ET.parse(version/'version.xml').getroot().findall('file'):
    name=f.findtext('physical_name')
    staged=version/name;downloaded=projects[0]/name
    want=hashlib.sha256(staged.read_bytes()).hexdigest()
    actual=hashlib.sha256(downloaded.read_bytes()).hexdigest()
    assert want==actual,(name,want,actual)
    hashes.append(dict(file=name,size=downloaded.stat().st_size,staged_sha256=want,downloaded_sha256=actual))
(e/'application-download-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
shutil.copy2(s/'acceptance-bundle-CabbageA/BUILD.json',e/'application-build.json')
native={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (runtime/'bin/scaling_cpu',runtime/'bin/gmp_reference')}
(e/'native-binary-hashes.json').write_text(json.dumps(native,indent=2)+'\n')
shutil.copy2(runtime/'results/build.json',e/'native-build.json')
# Private consistent database backup stays beside the private database and keys.
with (s/'pilot-database.sql').open('w') as out:
    subprocess.run([str(s/'root/usr/bin/mariadb-dump'),'--no-defaults','--protocol=TCP','-h127.0.0.1','-uroot','--single-transaction','fifth42'],stdout=out,check=True)
print('Captured database records, validated uploaded output, and matching downloaded application hashes',flush=True)
