"""Install only the private Mac pilot's homepage; preserve BOINC state/discovery."""
import argparse,datetime,hashlib,json,shutil,xml.etree.ElementTree as E
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--stock',required=True);a=p.parse_args()
stock=Path(a.stock).resolve();source=Path(__file__).resolve().parent
config=E.parse(stock/'project/config.xml')
assert config.getroot().findtext('config/master_url')=='http://127.0.0.1:8765/fifth42/','Private pilot URL required'
assert (stock/'MAC_APPLICATION_MacMetal141.json').is_file(),'This recipe targets the new Mac pilot only'
assert json.loads((source/'fifthpower-assets/pilot.json').read_text())['TEST_ONLY'] is True
user=stock/'project/html/user';stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup=stock/'homepage-backups'/stamp;backup.mkdir(parents=True,exist_ok=False)
shutil.copy2(user/'index.php',backup/'index.php')
assets=user/'fifthpower-assets'
if assets.exists():shutil.copytree(assets,backup/'fifthpower-assets')
staging=user/('fifthpower-stage-'+stamp);shutil.copytree(source/'fifthpower-assets',staging)
if assets.exists():shutil.rmtree(assets)
staging.replace(assets)
candidate=user/('index-stage-'+stamp+'.php');shutil.copy2(source/'index.php',candidate);candidate.replace(user/'index.php')
report=dict(backup=str(backup),installed=['index.php']+['fifthpower-assets/'+str(f.relative_to(assets)) for f in sorted(assets.rglob('*')) if f.is_file()],
 schedulers_sha256=hashlib.sha256((user/'schedulers.txt').read_bytes()).hexdigest(),TEST_ONLY=True,production_changes=False)
(backup/'DEPLOYMENT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
