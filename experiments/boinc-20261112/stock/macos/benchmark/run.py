"""Run six bounded TEST_ONLY replays sequentially; never touch production."""
import hashlib,json,os,statistics,subprocess,time,traceback
from pathlib import Path
s=Path('/pilot/mac-server');e=Path('/evidence/mac-benchmark');e.mkdir(exist_ok=True)
here=Path(os.environ['HERE']);runtime=Path(os.environ['RUNTIME'])
mysql=[str(s/'root/usr/bin/mariadb'),'--no-defaults','--protocol=TCP','-h127.0.0.1','-uroot','--batch','--skip-column-names','fifth42','-e']
manifest=s/'benchmark/full42.json';mh=hashlib.sha256(manifest.read_bytes()).hexdigest()
expected_points=sum(p['points'] for p in json.loads(manifest.read_text())['packets'])
assert expected_points==789435567
trials=[];started=time.monotonic();status_path=e/'STATUS.json'
def atomic(path,value):
 t=path.with_suffix('.tmp');t.write_text(json.dumps(value,indent=2)+'\n');t.replace(path)
def sql(q):return subprocess.check_output(mysql+[q],text=True,stderr=subprocess.DEVNULL).strip()
def status(state,**fields):
 atomic(status_path,dict(state=state,TEST_ONLY=True,new_scientific_coverage=False,manifest_sha256=mh,positions_per_trial=expected_points,accepted_trials=len(trials),trials=trials,**fields))
try:
 for i in range(1,4):
  for backend,av,bundle in [('cpu',1,'client-bundle'),('gpu',3,'metal-bundle-141')]:
   name=f'mac_m4_bench_{backend}_{i:02d}_20261113'
   existing=sql(f"SELECT id FROM workunit WHERE name='{name}'")
   if existing:
    assert backend=='cpu' and i==1,'Unexpected pre-existing benchmark; inspect instead of reusing'
   else:
    command=['python3',str(here/'stock/submit.py'),'--stock',str(s),'--runtime',str(runtime),'--manifest',str(manifest),'--name',name,'--app-version-id',str(av),'--build','A','--backend',backend,'--engine',str(s/bundle/'engine-identity')]
    atomic(e/(name+'-command.json'),command)
    with (e/(name+'-submit.log')).open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
   status('waiting',workunit=name,backend=backend)
   print('Waiting for '+name,flush=True)
   deadline=time.monotonic()+600
   while True:
    if time.monotonic()>deadline:raise TimeoutError('No canonical benchmark within 600 seconds: '+name)
    canonical=sql(f"SELECT canonical_resultid FROM workunit WHERE name='{name}'")
    if canonical and int(canonical)>0:break
    failed=sql(f"SELECT id,outcome,exit_status FROM result WHERE workunitid=(SELECT id FROM workunit WHERE name='{name}') AND outcome IN (3,4,6,7)")
    if failed:raise RuntimeError('Benchmark failed; inspect result '+failed)
    time.sleep(5)
   rid=int(canonical)
   audit=json.loads((s/f'validator-audit/{rid}.json').read_text())
   assert audit['scientifically_accepted'] is True and audit['boinc_app_version_id']==av and audit['positions']==expected_points
   result_path=s/Path(audit['uploaded_output']).relative_to('/pilot/mac-server')
   result=json.loads(result_path.read_text())
   assert result['manifest_sha256']==mh and result['completed_prefix']==42 and result['resumed_prefix']==0
   if backend=='gpu':assert result['metal_selftest_passed'] is True and result['metal_device_name']=='Apple M4' and result['boinc_gpu_device_num']==0
   times=sql(f'SELECT elapsed_time,cpu_time,app_version_id,outcome,validate_state,server_state FROM result WHERE id={rid}').split('\t')
   assert list(map(int,times[2:]))==[av,1,1,5],times
   for suffix,data in [('result.json',result),('audit.json',audit)]:atomic(e/(name+'-'+suffix),data)
   trial=dict(name=name,backend=backend,repeat=i,result_id=rid,positions=expected_points,packets=42,
    driver_seconds=result['elapsed_seconds'],native_rpc_seconds=sum(r['native_seconds'] for r in result['receipts']),
    engine_seconds=sum(r['response']['engine_seconds'] for r in result['receipts']),
    kernel_seconds=sum(r['response']['kernel_seconds'] for r in result['receipts']),
    boinc_elapsed_seconds=float(times[0]),boinc_cpu_seconds=float(times[1]),independent_GMP_accepted=True)
   trials.append(trial);status('accepted',last_workunit=name)
   print(json.dumps(trial),flush=True)
 medians={backend:{metric:statistics.median(t[metric] for t in trials if t['backend']==backend) for metric in ('driver_seconds','native_rpc_seconds','engine_seconds','boinc_elapsed_seconds')} for backend in ('cpu','gpu')}
 speedup={metric:medians['cpu'][metric]/medians['gpu'][metric] for metric in medians['cpu']}
 status('complete',median_seconds=medians,cpu_over_gpu_time_ratio=speedup,controller_seconds=time.monotonic()-started)
 print(json.dumps(dict(median_seconds=medians,cpu_over_gpu_time_ratio=speedup)),flush=True)
except BaseException as failure:
 status('failed',error=str(failure));traceback.print_exc();raise
