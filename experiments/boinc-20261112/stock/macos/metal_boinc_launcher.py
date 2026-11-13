"""M4-only private BOINC pilot: prove the unique allocated Metal device first."""
import argparse,json,os,random,re,subprocess,sys,xml.etree.ElementTree as E
from pathlib import Path

def select_device(init_data,number,devices):
    root=E.parse(init_data).getroot()
    if root.tag!='app_init_data' or root.findtext('gpu_type')!='apple_gpu':raise ValueError('BOINC Apple GPU allocation required')
    declared=root.findtext('gpu_device_num')
    if declared is None or not declared.isascii() or not declared.isdecimal():raise ValueError('Explicit BOINC metadata device number required')
    if number is None:number=declared
    if not isinstance(number,str) or not number.isascii() or not number.isdecimal() or int(declared)!=int(number):raise ValueError('Wrapper and BOINC allocation disagree')
    # This pilot supports exactly one physical M4-family GPU. No implicit zero,
    # vendor-index guessing, multi-GPU mapping or paravirtual device is accepted.
    if int(number)!=0 or not isinstance(devices,list) or len(devices)!=1:raise ValueError('Unique BOINC/Metal M4 allocation required')
    device=devices[0]
    if not re.fullmatch(r'Apple M4(?: (?:Pro|Max))?',device.get('name','')):raise ValueError('This physical GPU pilot is restricted to the M4 family')
    registry=device.get('registry_id')
    if not isinstance(registry,str) or not registry.isascii() or not registry.isdecimal() or not 0<int(registry)<2**64:raise ValueError('Invalid Metal registry ID')
    return registry

def arithmetic_cases():
    edge=[0,1,-1,2,-2,2**32-1,2**32,2**32+1,200000000000,-200000000000]
    rows=[(a,b) for a in edge for b in edge];rng=random.Random(424242)
    return rows+[(rng.randint(-200000000000,200000000000),rng.randint(-200000000000,200000000000)) for _ in range(1000)]

def expected(a,b):
    p=a**5;q=b**5
    def limbs(n):return [(n>>shift)&(2**64-1) for shift in (0,64,128)]
    return [*limbs(p),*limbs(q),*limbs(p+q),*limbs(-p-q),*limbs(5*a*a),int(p<q),int(p==q)]

def verify_arithmetic(rows,response):
    values=response.get('arithmetic')
    if not isinstance(values,list) or len(values)!=len(rows):raise ValueError('Incomplete Metal arithmetic self-test')
    for value,(a,b) in zip(values,rows):
        actual=[*(n for key in ('p','q','sum','negative','square5') for n in value[key]),value['lt'],value['eq']]
        if any(type(n) is not int for n in actual) or actual!=expected(a,b):raise ValueError('Metal exact arithmetic self-test failed')

def main():
    p=argparse.ArgumentParser();p.add_argument('--boinc-device');p.add_argument('--init-data',default='init_data.xml')
    p.add_argument('--manifest',required=True);p.add_argument('--engine',required=True);p.add_argument('--output',required=True)
    p.add_argument('--max-seconds',type=int,default=600);p.add_argument('--pause-after',type=int,default=-1);p.add_argument('--pause-seconds',type=int,default=60)
    a=p.parse_args();engine=Path(a.engine).resolve()
    probe=subprocess.run([str(engine),'--list-devices'],capture_output=True,text=True,check=True,timeout=30)
    devices=json.loads(probe.stdout)['devices'];registry=select_device(a.init_data,a.boinc_device,devices)
    allocated_number=int(E.parse(a.init_data).getroot().findtext('gpu_device_num'))
    environment=dict(os.environ,FIFTH42_METAL_REGISTRY_ID=registry)
    rows=arithmetic_cases();payload='ARITH_V1 '+str(len(rows))+'\n'+''.join(f'{a} {b}\n' for a,b in rows)
    test=subprocess.run([str(engine),'--arithmetic'],input=payload,capture_output=True,text=True,env=environment,timeout=120)
    if test.returncode:raise RuntimeError('Metal self-test execution failed: '+test.stderr)
    verify_arithmetic(rows,json.loads(test.stdout))
    command=[sys.executable,'-s',str(Path(__file__).with_name('science_driver.py')),'--manifest',a.manifest,'--engine',str(engine),
        '--output',a.output,'--build','A','--backend','metal','--metal-device-registry-id',registry,'--max-seconds',str(a.max_seconds),
        '--pause-after',str(a.pause_after),'--pause-seconds',str(a.pause_seconds)]
    subprocess.run(command,check=True,timeout=750)
    from science_driver import atomic
    result=json.loads(Path(a.output).read_text())
    if result.get('backend')!='gpu' or result.get('metal_device_registry_id')!=registry:raise ValueError('Metal result allocation identity differs')
    result.update(boinc_gpu_device_num=allocated_number,metal_device_name=devices[0]['name'],metal_selftest_cases=len(rows),metal_selftest_passed=True)
    atomic(a.output,result)

if __name__=='__main__':main()
