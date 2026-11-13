#!/usr/bin/env python3
"""Actual private BOINC CPU lifecycle probes; run inside stock/with_stack.sh."""
import hashlib,json,os,re,shutil,signal,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path

S=Path(os.environ['STOCK']);H=Path(os.environ['HERE']);R=Path(os.environ['RUNTIME']);E=Path('/evidence')
URL='http://127.0.0.1:8765/fifth42/'
MYSQL=[str(S/'root/usr/bin/mariadb'),'--no-defaults','--protocol=TCP','-h127.0.0.1','-uroot','--batch','--skip-column-names','fifth42','-e']
summary=dict(TEST_ONLY=True,new_scientific_coverage=False,tests={})
if (E/'summary.json').exists():summary=json.loads((E/'summary.json').read_text())

def event(message):print(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),message,flush=True)
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)
def run(args,cwd=None,check=True):
    result=subprocess.run([str(x) for x in args],cwd=cwd,capture_output=True,text=True,timeout=180)
    redacted=list(map(str,args))
    if '--passwd' in redacted:redacted[redacted.index('--passwd')+1]='<REDACTED>'
    with (E/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(command=redacted,cwd=str(cwd),returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))+'\n')
    if check and result.returncode:raise RuntimeError(f'Command {redacted[0]} failed ({result.returncode}); see commands.jsonl')
    return result.stdout
def sql(q):return run(MYSQL+[q]).strip()
def bc(*args):
    key=(S/'client/gui_rpc_auth.cfg').read_text().strip()
    return run([S/'root/usr/bin/boinccmd','--host','127.0.0.1:31420','--passwd',key,*args],check=False)
def wait(label,predicate,timeout=240):
    deadline=time.monotonic()+timeout;last=0
    while time.monotonic()<deadline:
        result=predicate()
        if result:return result
        if time.monotonic()-last>15:event('waiting: '+label);last=time.monotonic()
        time.sleep(1)
    raise TimeoutError(label)
def passed(name,data):
    summary['tests'][name]=dict(status='passed',**data);save(E/'summary.json',summary);event('PASS '+name)
def rows(name):
    assert re.fullmatch(r'[A-Za-z0-9_-]+',name)
    q="SELECT JSON_OBJECT('id',r.id,'name',r.name,'workunitid',w.id,'canonical',w.canonical_resultid,'need_validate',w.need_validate,'error_mask',w.error_mask,'server_state',r.server_state,'outcome',r.outcome,'validate_state',r.validate_state,'exit_status',r.exit_status,'app_version_id',r.app_version_id,'hostid',r.hostid,'cpu_time',r.cpu_time,'elapsed_time',r.elapsed_time,'sent_time',r.sent_time,'received_time',r.received_time,'transition_time',w.transition_time) FROM result r JOIN workunit w ON w.id=r.workunitid WHERE w.name='%s' ORDER BY r.id"%name
    return [json.loads(x) for x in sql(q).splitlines() if x]
def submit(name,version,build,args='',manifest=None):
    run(['python3',H/'stock/submit.py','--stock',S,'--runtime',R,'--manifest',manifest or S/'controls.json','--name',name,'--app-version-id',version,'--build',build,'--command-line',args])
    if (S/'client/gui_rpc_auth.cfg').exists():bc('--project',URL,'update')
def stage(label,build,version):
    run(['python3',H/'stock/stage_application.py','--stock',S,'--runtime',R,'--label',label,'--build',build,'--version',version])
    run(['php','bin/update_versions','--noconfirm','--verbose'],cwd=S/'project')
    return int(sql(f'SELECT id FROM app_version WHERE version_num={int(float(version)*100)}'))
def start_client():
    run(['bash',H/'stock/start_client.sh',S])
    wait('client RPC',lambda:(S/'client/gui_rpc_auth.cfg').exists() and 'Tasks' in bc('--get_tasks'),30)
    bc('--project',URL,'allowmorework');bc('--project',URL,'update')
def stop_client(label):
    bc('--quit');pid=int((S/'client.pid').read_text())
    def stopped():
        p=Path(f'/proc/{pid}/stat');return not p.exists() or p.read_text().split(') ',1)[1].startswith('Z')
    wait('client quit',stopped,20)
    shutil.copy2(S/'client-console.log',E/f'client-{label}.log')
    (S/'client.pid').unlink(missing_ok=True)
    active=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        except (FileNotFoundError,PermissionError):continue
        if any(x in cmd for x in ('science_driver.py','scaling_cpu','fifth42_LifecycleA_wrapper','fifth42_LifecycleB_wrapper')):active.append(cmd)
    assert not active,active
def slot(name,prefix):
    for p in (S/'client/slots').glob('*'):
        try:
            init=ET.parse(p/'init_data.xml').getroot()
            if not init.findtext('result_name','').startswith(name+'_'):continue
            checkpoint=json.loads((p/'checkpoint.json').read_text())
            if checkpoint['completed_prefix']==prefix:return p
        except (FileNotFoundError,ET.ParseError,json.JSONDecodeError):continue
def snapshot_slot(path,label):
    dest=E/'slots'/label;dest.mkdir(parents=True,exist_ok=True)
    for name in ('checkpoint.json','receipts.json','science.stdout','science.stderr','fraction_done.txt'):
        if (path/name).exists():shutil.copy2(path/name,dest/name)
    state=ET.parse(S/'client/client_state.xml').getroot()
    save(dest/'active-tasks.json',[{c.tag:c.text for c in a} for a in state.findall('.//active_task')])
def preserve(row):
    files=list((S/'project/upload').rglob(row['name']+'_r*_0'))
    if files:
        assert len(files)==1,files
        p=files[0];(E/'uploaded').mkdir(exist_ok=True);shutil.copy2(p,E/'uploaded'/p.name)
        return json.loads(p.read_text()),hashlib.sha256(p.read_bytes()).hexdigest()
    return None,None
def accepted(name,packets=3,positions=9,timeout=240):
    def found():
        return next((r for r in rows(name) if r['canonical']==r['id'] and r['validate_state']==1),None)
    row=wait('canonical '+name,found,timeout)
    assert row['exit_status']==0 and row['outcome']==1 and row['server_state']==5,row
    audit=json.loads((S/'validator-audit'/f"{row['id']}.json").read_text())
    assert audit['scientifically_accepted'] and audit['packets']==packets and audit['positions']==positions,audit
    assert audit['TEST_ONLY'] and audit['new_scientific_coverage'] is False
    save(E/'validator-audit'/f"{row['id']}.json",audit)
    output,digest=preserve(row);return row,output,digest
def check_downloads(label,version):
    d=S/'project/apps/fifth42'/version/'x86_64-pc-linux-gnu';client=next((S/'client/projects').iterdir());records=[]
    for f in ET.parse(d/'version.xml').getroot().findall('file'):
        name=f.findtext('physical_name');a=(d/name).read_bytes();b=(client/name).read_bytes()
        assert a==b,name
        records.append(dict(file=name,bytes=len(a),sha256=hashlib.sha256(b).hexdigest()))
    save(E/f'downloaded-{label}.json',records);return records

def force_validator(wuid,label):
    args=['../bin/script_validator','--app','fifth42','--init_script','fifth42_validate result_id files','--wu_id',str(wuid),'--one_pass','-d','3']
    result=subprocess.run(args,cwd=S/'project/tmp',capture_output=True,text=True,timeout=180)
    log=result.stdout+result.stderr;(E/f'{label}.log').write_text(log)
    assert result.returncode==0,(label,result.returncode)
    return log

def infrastructure_tests(b):
    for fault in ('oracle','database'):
        name='outage_'+fault
        bc('--project',URL,'nomorework')
        if not rows(name):
            submit(name,b,'B')
        cfgpath=S/'validator-config.json';original=json.loads(cfgpath.read_text());broken=json.loads(cfgpath.read_text())
        if fault=='oracle':broken['gmp_reference']='/pilot/TEST_ONLY_MISSING_GMP'
        else:broken['mysql_command']+=['--port=33306']
        save(cfgpath,broken)
        try:
            # Install the fault before permitting assignment/reporting, so the
            # normal validator cannot accept a fast control ahead of the probe.
            if not any(r['server_state']==5 and r['outcome']==1 for r in rows(name)):
                bc('--project',URL,'allowmorework');bc('--project',URL,'update')
                wait('outage assignment',lambda:any(r['server_state'] in (4,5) for r in rows(name)))
            bc('--project',URL,'nomorework')
            row=wait('uploaded '+name,lambda:next((r for r in rows(name) if r['server_state']==5 and r['outcome']==1),None))
            log=force_validator(row['workunitid'],name+'-fault')
            assert 'transient failure' in log,log
            pending=rows(name)
            assert pending[0]['validate_state'] in (0,4) and pending[0]['canonical']==0 and pending[0]['outcome']==1,pending
            assert not any(r['validate_state']==2 for r in pending),pending
            _,before_digest=preserve(pending[0]);save(E/f'{name}-deferred.json',pending)
        finally:save(cfgpath,original)
        force_validator(row['workunitid'],name+'-recovery')
        accepted_row,output,digest=accepted(name)
        after=rows(name);original_result=next(r for r in after if r['id']==pending[0]['id'])
        _,after_digest=preserve(original_result)
        assert original_result['validate_state']==1 and after_digest==before_digest
        for extra in after:
            if extra['server_state']==4:bc('--task',URL,extra['name'],'abort')
        passed(name,dict(deferred=pending,accepted=accepted_row,all_attempts=after,original_upload_sha256=after_digest,recheck='stock --wu_id --one_pass after dependency restored'))

def finish():
    bc('--project',URL,'nomorework');bc('--project',URL,'update')
    stop_client('final')
    for table in ('result','workunit','app_version'):
        (E/f'server-{table}.tsv').write_text(run([x for x in MYSQL if x!='--skip-column-names']+[f'SELECT * FROM {table} ORDER BY id']))
    with (S/'lifecycle-database.sql').open('w') as f:
        subprocess.run([S/'root/usr/bin/mariadb-dump','--no-defaults','--protocol=TCP','-h127.0.0.1','-uroot','--single-transaction','fifth42'],stdout=f,check=True)
    summary['status']='passed';save(E/'summary.json',summary);event('ALL CPU LIFECYCLE TESTS PASSED')

def main():
    event('starting real BOINC lifecycle suite')
    run(['python3',H/'scripts/make_manifest.py','--catalog',R/'data/packets.jsonl','--output',S/'controls.json','--names','control-cap100-r12','control-cap42-r12','control-cap2951-r-2002'])
    a=stage('LifecycleA','A','1.00')
    submit('recovery_A',a,'A','--packet-delay 2 --pause-after 2 --pause-seconds 60')
    start_client()
    p=wait('real durable prefix 2',lambda:slot('recovery_A',2));time.sleep(5)
    snapshot_slot(p,'recovery-before-stop');before=rows('recovery_A');assert before[-1]['app_version_id']==a
    a_files=check_downloads('A','1.00')
    b=stage('LifecycleB','B','1.01')
    assert rows('recovery_A')[-1]['app_version_id']==a
    stop_client('recovery-before-restart');snapshot_slot(p,'recovery-after-stop')
    start_client();row,output,digest=accepted('recovery_A')
    assert output['resumed_prefix']==2 and len(output['attempts'])==2,output
    assert [r['attempt'] for r in output['receipts'][:2]]==[output['attempts'][0]]*2
    assert output['receipts'][2]['attempt']==output['attempts'][1]
    passed('checkpoint-recovery',dict(result=row,output_sha256=digest,resumed_prefix=2,attempts=output['attempts']))
    submit('upgrade_B',b,'B');row,output,digest=accepted('upgrade_B');assert output['build']=='B'
    b_files=check_downloads('B','1.01')
    assert next(x['sha256'] for x in a_files if x['file'].endswith('science_driver.py'))!=next(x['sha256'] for x in b_files if x['file'].endswith('science_driver.py'))
    passed('A-to-B-upgrade',dict(result=row,A_app_version=a,B_app_version=b,output_sha256=digest))

    submit('retry_B',b,'B','--packet-delay 2 --pause-after 1 --pause-seconds 60')
    p=wait('retry prefix 1',lambda:slot('retry_B',1));snapshot_slot(p,'retry-before-abort')
    first=rows('retry_B')[-1];bc('--task',URL,first['name'],'abort');bc('--project',URL,'update')
    row,output,digest=accepted('retry_B',timeout=300)
    attempts=rows('retry_B');assert len(attempts)>=2 and row['id']!=first['id'],attempts
    assert output['resumed_prefix']==0 and len(output['attempts'])==1,output
    assert sum(r['id']==r['canonical'] and r['validate_state']==1 for r in attempts)==1
    passed('failed-attempt-retry',dict(attempts=attempts,output_sha256=digest,recomputed_positions=9))

    for kind in ('identity','count','truncated'):
        name='negative_'+kind;submit(name,b,'B','--corrupt-output '+kind)
        row=wait('scientific rejection '+name,lambda:next((r for r in rows(name) if r['validate_state']==2),None))
        assert row['exit_status']==0 and row['canonical']==0,row
        output,digest=preserve(row);run(['bin/cancel_jobs','--name',name],cwd=S/'project')
        bc('--project',URL,'update')
        passed(name,dict(result=row,output_sha256=digest))

    manifest=S/'representative.json'
    run(['python3',H/'scripts/make_manifest.py','--catalog',R/'data/packets.jsonl','--output',manifest,'--names','ada-upper-w0-b0'])
    submit('representative_B',b,'B',manifest=manifest)
    row,output,digest=accepted('representative_B',1,49491764)
    passed('representative-CPU',dict(result=row,output_sha256=digest,native_seconds=sum(r['native_seconds'] for r in output['receipts']),driver_seconds=output['elapsed_seconds']))

    infrastructure_tests(b)
    finish()

if __name__=='__main__':main()
