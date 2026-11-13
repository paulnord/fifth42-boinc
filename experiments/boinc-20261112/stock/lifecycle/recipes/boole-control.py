import hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
B=Path('/pilot');client=B/'client'
if sys.argv[1]=='inspect':
    state=ET.parse(client/'client_state.xml').getroot()
    tasks=[{c.tag:c.text for c in a} for a in state.findall('.//active_task')]
    hashes=[]
    for p in (client/'projects').glob('*/*'):
        if p.is_file() and p.name.startswith('fifth42_Boole'):
            hashes.append(dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    slots=[]
    for p in (client/'slots').glob('*'):
        item=dict(slot=p.name)
        for name in ('checkpoint.json','receipts.json'):
            if (p/name).exists():item[name]=json.loads((p/name).read_text())
        if (p/'science.stdout').exists():item['stdout']=(p/'science.stdout').read_text()
        slots.append(item)
    print(json.dumps(dict(active_tasks=tasks,downloads=hashes,slots=slots,
        coprocs=ET.tostring(state.find('coprocs'),encoding='unicode') if state.find('coprocs') is not None else None,
        app_versions=[ET.tostring(v,encoding='unicode') for v in state.findall('app_version')])))
else:
    key=(client/'gui_rpc_auth.cfg').read_text().strip()
    cmd=[str(B/'runtime/usr/bin/boinccmd'),'--host','127.0.0.1:31422','--passwd',key,*sys.argv[1:]]
    r=subprocess.run(cmd,capture_output=True,text=True)
    print(r.stdout);print(r.stderr,file=sys.stderr)
    sys.exit(r.returncode)
