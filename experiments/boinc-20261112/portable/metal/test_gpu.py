"""Real GPU integer, allocation, capacity, interruption and recovery checks."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
from test_arithmetic import cases,expected

def run_tests(base,registry):
    base=Path(base);runtime=base/'runtime';engine=runtime/'bin/scaling_gpu';kit=base/'metal-kit'
    environment=dict(os.environ,FIFTH42_METAL_REGISTRY_ID=registry)
    rows=cases()
    result=subprocess.run([str(engine),'--arithmetic'],input='ARITH_V1 '+str(len(rows))+'\n'+''.join(f'{a} {b}\n' for a,b in rows),
        env=environment,capture_output=True,text=True,check=True,timeout=120)
    values=json.loads(result.stdout)['arithmetic'];assert len(values)==len(rows)
    for value,(a,b) in zip(values,rows):
        actual=[*(n for key in ('p','q','sum','negative','square5') for n in value[key]),value['lt'],value['eq']]
        assert actual==expected(a,b),(a,b)
    # An allocation that was not in the actual enumerated list must fail.
    invalid=dict(environment,FIFTH42_METAL_REGISTRY_ID='18446744073709551615')
    probe=subprocess.run([str(engine),'--arithmetic'],input='ARITH_V1 0\n',env=invalid,capture_output=True,text=True,timeout=30)
    assert probe.returncode!=0 and 'unavailable' in probe.stderr
    sys.path.insert(0,str(runtime));from engine_session import EngineSession
    sys.path.insert(0,str(kit/'app'));from colab_bench import combine,verify
    packets=[json.loads(line) for line in (runtime/'data/packets.jsonl').read_text().splitlines()]
    with EngineSession([str(engine)],'gpu',time.monotonic()+120,environment=environment) as session:
        assert session.ready['gpu_api']=='metal' and session.ready['device_registry_id']==registry
        for row in packets:
            if row['group']=='control':
                response,_=session.run(row['packet']);verify(row['packet'],response,'gpu',row['expected'])
    control=next(r for r in packets if r['group']=='control')
    doubled=combine([control,control])[0]['packet']
    with EngineSession([str(engine),'--capacity','1'],'gpu',time.monotonic()+120,environment=environment) as session:
        response,_=session.run(doubled)
        assert response.get('box_complete') is False and 'capacity exceeded' in response['error']
    parent_env=dict(environment,FIFTH42_RUNTIME=str(runtime),FIFTH42_PARENT_TEST_ENGINE=str(engine))
    run=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(Path(__file__).resolve().parents[2]/'tests'),
        '-p','test_parent_lifetime.py','-v'],env=parent_env,capture_output=True,text=True,timeout=45)
    (base/'METAL_PARENT_TEST.log').write_text(run.stdout+run.stderr)
    assert run.returncode==0,'Metal engine parent-lifetime test failed'
    recovery=base/'metal-recovery';recovery.mkdir(exist_ok=False)
    command=[sys.executable,str(kit/'app/science_driver.py'),'--engine',str(engine),'--manifest',str(kit/'controls.json'),
        '--build','A','--backend','metal','--metal-device-registry-id',registry]
    with (recovery/'interrupted.log').open('w') as log:
        process=subprocess.Popen(command+['--pause-after','1'],cwd=recovery,stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+45
            while not (recovery/'checkpoint.json').exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
            assert json.loads((recovery/'checkpoint.json').read_text())['completed_prefix']==1
            process.kill();process.wait(timeout=5)
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=5)
    subprocess.run(command,cwd=recovery,check=True,timeout=120)
    result=json.loads((recovery/'result.json').read_text())
    assert result['resumed_prefix']==1 and result['completed_prefix']==3 and len(result['receipts'])==3 and len(result['attempts'])==2
    # Fresh independent oracle on the resumed real GPU output.
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'app'))
    from validate_result import validate
    acceptance=validate(kit/'controls.json',recovery/'result.json',runtime/'bin/gmp_reference',hashlib.sha256(engine.read_bytes()).hexdigest(),'A','gpu')
    report=dict(status='passed',gpu_execution=True,registry_id=registry,arithmetic_cases=len(rows),
        bad_allocation_rejected=True,capacity_overflow_rejected=True,parent_death_verified=True,
        checkpoint_resumed_prefix=1,attempts=2,fresh_gmp_control_acceptance=acceptance)
    (base/'METAL_GPU_TESTS.json').write_text(json.dumps(report,indent=2)+'\n');return report
