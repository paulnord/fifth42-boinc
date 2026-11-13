#!/usr/bin/env python3
"""Drive an actual remote BOINC client through owned namespaces and SSH."""
import hashlib,json,os,re,shutil,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
B=Path(os.environ['FIFTH42_LAB']);E=B/'evidence/remote';E.mkdir(exist_ok=True)
HOST='boole';REMOTE='/home/pnord/boinc-fifth42-client-test-20261113';UNIT='fifth42-boinc-native-client-20261113'
URL='http://127.0.0.1:8765/fifth42/'
SSH=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',HOST]
summary=dict(TEST_ONLY=True,new_scientific_coverage=False,client=HOST,tests={})
def event(x):print(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),x,flush=True)
def save(name,data):(E/name).write_text(json.dumps(data,indent=2)+'\n')
def run(args,check=True):
    r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120)
    with (E/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(command=list(map(str,args)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))+'\n')
    if check and r.returncode:raise RuntimeError(f'Command failed: {args[0]}; see remote/commands.jsonl')
    return r.stdout
def wait(label,predicate,seconds=240):
    end=time.monotonic()+seconds;last=0
    while time.monotonic()<end:
        value=predicate()
        if value:return value
        if time.monotonic()-last>15:event('waiting: '+label);last=time.monotonic()
        time.sleep(1)
    raise TimeoutError(label)
pid=int(run(['pgrep','-f','^python3 /recipe/remote-server-wait.py$']).strip())
NS=['nsenter','--target',str(pid),'--user','--mount','--net','--pid','--preserve-credentials','bash','/recipe/server-command.sh']
def server(*args):return run(NS+list(args))
def sql(q):return server('/pilot/boole-server/root/usr/bin/mariadb','--no-defaults','--protocol=TCP','-h127.0.0.1','-uroot','--batch','--skip-column-names','fifth42','-e',q).strip()
def client(*args,check=True):
    assert all(re.fullmatch(r'[A-Za-z0-9_:/.,+-]+',str(x)) for x in args)
    cmd="p=$(pgrep -f '^/bin/bash /recipe/boole-client.sh$'); test -n \"$p\"; nsenter --target \"$p\" --user --mount --net --pid --preserve-credentials env LD_LIBRARY_PATH=/pilot/runtime/usr/lib/x86_64-linux-gnu /usr/bin/python3 /recipe/boole-control.py "+' '.join(map(str,args))
    return run(SSH+[cmd],check)
def inspect():
    try:return json.loads(client('inspect',check=False))
    except (json.JSONDecodeError,RuntimeError):return None
def start():
    run(SSH+[f'systemd-run --user --unit={UNIT} --collect -p CPUQuota=200% -p MemoryMax=4G -p MemorySwapMax=0 -p TasksMax=128 -p RuntimeMaxSec=900 /usr/bin/nice -n 19 /bin/bash {REMOTE}/recipe/boole-namespace.sh /bin/bash /recipe/boole-client.sh'])
    wait('Boole client RPC',lambda:'Tasks' in client('--get_tasks',check=False),45)
    client('--set_run_mode','always');client('--set_gpu_mode','always');client('--project',URL,'allowmorework');client('--project',URL,'update')
def stop(label):
    client('--project',URL,'nomorework');client('--quit')
    wait('Boole namespace exit',lambda:not run(SSH+[f"systemctl --user is-active {UNIT} 2>/dev/null"],check=False).strip()=='active',30)
    run(SSH+[f'cp {REMOTE}/evidence/client-console.log {REMOTE}/evidence/client-{label}.log'])
    run(['scp','-q',f'{HOST}:{REMOTE}/evidence/client-{label}.log',str(E/f'client-{label}.log')])
    snapshot=run(SSH+['nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv,noheader'])
    (E/f'gpu-after-{label}.txt').write_text(snapshot)
    assert 'scaling_gpu' not in snapshot,snapshot
def row(name):
    q="SELECT JSON_OBJECT('id',r.id,'name',r.name,'canonical',w.canonical_resultid,'app_version_id',r.app_version_id,'hostid',r.hostid,'exit_status',r.exit_status,'outcome',r.outcome,'validate_state',r.validate_state,'elapsed_time',r.elapsed_time,'sent_time',r.sent_time,'received_time',r.received_time) FROM result r JOIN workunit w ON r.workunitid=w.id WHERE w.name='%s' ORDER BY r.id"%name
    return [json.loads(x) for x in sql(q).splitlines() if x]
def submit(name,version,backend,extra='',large=False):
    manifest='/pilot/boole-server/controls.json'
    if large:
        manifest='/pilot/boole-server/representative.json'
        server('python3','/source/experiments/boinc-20261112/scripts/make_manifest.py','--catalog','/pilot/science/runtime/data/packets.jsonl','--output',manifest,'--names','ada-upper-w0-b0')
    server('python3','/source/experiments/boinc-20261112/stock/submit.py','--stock','/pilot/boole-server','--runtime','/pilot/science/runtime','--manifest',manifest,'--name',name,'--app-version-id',version,'--build','B','--backend',backend,'--command-line',extra)
    client('--project',URL,'update')
def accepted(name,backend,packets=3,positions=9):
    def found():return next((r for r in row(name) if r['canonical']==r['id'] and r['validate_state']==1),None)
    r=wait('remote acceptance '+name,found)
    audit=json.loads((B/'work/boole-server/validator-audit'/f"{r['id']}.json").read_text())
    assert audit['packets']==packets and audit['positions']==positions and audit['scientifically_accepted'],audit
    output_path=B/'work/boole-server/project/upload'/Path(audit['uploaded_output']).relative_to('/pilot/boole-server/project/upload')
    output=json.loads(output_path.read_text());assert output['backend']==backend,output
    assert r['exit_status']==0 and r['outcome']==1
    (E/'uploaded').mkdir(exist_ok=True);shutil.copy2(output_path,E/'uploaded'/output_path.name)
    data=dict(result=r,audit=audit,output_sha256=hashlib.sha256(output_path.read_bytes()).hexdigest(),output=output)
    summary['tests'][name]=data;save('summary.json',summary);event('PASS '+name);return data

started=False;tunnel=False
try:
    # Every forwarded endpoint is a mode-0600 Unix socket beneath a private dir.
    run(SSH+[f'mkdir -p {REMOTE}/work/client'])
    run(['scp','-q',str(B/'work/boole-server/remote-account.xml'),f'{HOST}:{REMOTE}/work/client/account_127.0.0.1_8765_fifth42.xml'])
    run(['ssh','-M','-S',str(B/'ssh-control'),'-fNT','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ExitOnForwardFailure=yes','-o','StreamLocalBindMask=0177','-R',f'{REMOTE}/work/project.sock:{B}/work/server-http.sock',HOST]);tunnel=True
    cpu=int(sql("SELECT id FROM app_version WHERE version_num=110"));gpu=int(sql("SELECT id FROM app_version WHERE version_num=120"))
    started=True;start()
    submit('boole_cpu_controls',cpu,'cpu');accepted('boole_cpu_controls','emulated')
    submit('boole_cpu_representative',cpu,'cpu',large=True);accepted('boole_cpu_representative','emulated',1,49491764)
    submit('boole_gpu_controls',gpu,'gpu');accepted('boole_gpu_controls','gpu')
    submit('boole_gpu_representative',gpu,'gpu',large=True);accepted('boole_gpu_representative','gpu',1,49491764)
    submit('boole_gpu_recovery',gpu,'gpu','--pause-after 1 --pause-seconds 60 --packet-delay 2')
    def prefix():
        data=inspect()
        return data if data and any(s.get('checkpoint.json',{}).get('completed_prefix')==1 for s in data['slots']) else None
    before=wait('GPU durable prefix 1',prefix);time.sleep(4);save('gpu-before-restart.json',inspect())
    (E/'gpu-during-recovery.txt').write_text(run(SSH+['nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv,noheader']))
    stop('before-gpu-restart');started=False
    started=True;start()
    data=accepted('boole_gpu_recovery','gpu');assert data['output']['resumed_prefix']==1 and len(data['output']['attempts'])==2
    info=inspect();save('client-final.json',info)
    for version,platform in [('1.10','x86_64-pc-linux-gnu'),('1.20','x86_64-pc-linux-gnu__fifth42_cuda')]:
        root=B/'work/boole-server/project/apps/fifth42'/version/platform
        for f in ET.parse(root/'version.xml').getroot().findall('file'):
            name=f.findtext('physical_name');actual=next(x for x in info['downloads'] if x['file']==name)
            assert actual['sha256']==hashlib.sha256((root/name).read_bytes()).hexdigest(),name
    save('download-hash-check.json',dict(all_downloads_match=True,files=info['downloads']))
    stop('final');started=False
    for table in ('result','workunit','app_version','host'):
        # Host table is hardware metadata; user/account table is deliberately absent.
        (E/f'server-{table}.tsv').write_text(sql(f'SELECT * FROM {table} ORDER BY id'))
    summary['status']='passed';save('summary.json',summary);event('ALL BOOLE CPU/GPU TESTS PASSED')
finally:
    if started:
        try:stop('failure')
        except Exception:run(SSH+[f'systemctl --user stop {UNIT}'],check=False)
    if tunnel:run(['ssh','-S',str(B/'ssh-control'),'-O','exit',HOST],check=False)
    (B/'work/stop-remote-server').touch()
