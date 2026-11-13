import json,os,subprocess,time
from pathlib import Path
s=Path(os.environ['STOCK'])
mysql=[str(s/'root/usr/bin/mariadb'),'--no-defaults','--protocol=TCP','-h127.0.0.1','-uroot','--batch','--skip-column-names','fifth42','-e']
deadline=time.monotonic()+480
while time.monotonic()<deadline:
    row=subprocess.check_output(mysql+["SELECT w.id,w.canonical_resultid,r.id,r.server_state,r.outcome,r.validate_state,r.app_version_id FROM workunit w LEFT JOIN result r ON r.id=w.canonical_resultid WHERE w.name='cabbage_pilot_control'"],text=True).strip()
    print(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),row,flush=True)
    if row:
        fields=row.split('\t')
        if fields[1]!='0' and fields[2]!='NULL':
            assert fields[3:6]==['5','1','1'],fields
            audit=json.loads((s/'validator-audit'/f'{fields[2]}.json').read_text())
            assert audit['scientifically_accepted'] is True and audit['packets']==3 and audit['positions']==9,audit
            assert audit['TEST_ONLY'] is True and audit['new_scientific_coverage'] is False,audit
            print(json.dumps(audit,indent=2),flush=True)
            break
    time.sleep(2)
else:
    raise TimeoutError('No canonical, scientifically accepted control within 480 seconds')
