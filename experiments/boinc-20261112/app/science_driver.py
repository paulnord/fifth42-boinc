#!/usr/bin/env python3
"""Bounded TEST_ONLY Fifth42 packet replay; BOINC owns scheduling and delivery."""
import argparse, hashlib, json, os, time, uuid
from pathlib import Path
from colab_bench import tasks, verify
from engine_session import EngineSession

APPLICATION_BUILD="prototype-dev"

def digest(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def atomic(path, data):
    path=Path(path); tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w') as f:
        json.dump(data,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
def load_manifest(path):
    raw=Path(path).read_bytes(); m=json.loads(raw)
    if m.get('schema')!='fifth42-boinc-test-v1' or m.get('TEST_ONLY') is not True or m.get('new_scientific_coverage') is not False: raise ValueError('Only TEST_ONLY manifest allowed')
    if not isinstance(m.get('packets'),list) or not 1<=len(m['packets'])<=42: raise ValueError('Invalid bounded packet list')
    for r in m['packets']:
        if digest(r['packet'].encode())!=r['packet_sha256']: raise ValueError('Packet identity')
        cap,ts=tasks(r['packet'])
        if type(r['cap']) is not int or cap!=r['cap'] or type(r['points']) is not int or r['points']!=sum(t['points'] for t in ts): raise ValueError('Packet metadata')
    return m,digest(raw)
def check_receipt(r,row,index,backend='emulated'):
    if type(r.get('index')) is not int or r['index']!=index or r.get('packet_sha256')!=row['packet_sha256']: raise ValueError('Receipt identity/order')
    verify(row['packet'],r['response'],backend,row['expected'])
def main(a):
    if APPLICATION_BUILD != 'prototype-dev' and a.build != APPLICATION_BUILD: raise ValueError('Executable build identity mismatch')
    manifest,mhash=load_manifest(a.manifest); engine=Path(a.engine).resolve()
    backend='gpu' if a.backend=='gpu' else 'emulated'
    engine_environment=None
    if backend=='gpu':
        if a.gpu_device is None or not a.gpu_device.isascii() or not a.gpu_device.isdecimal():
            raise ValueError('GPU execution requires the BOINC allocated device number')
        # The unchanged native engine selects logical device zero. Restrict its
        # visibility to BOINC's allocated physical device before CUDA initializes.
        engine_environment=dict(os.environ,CUDA_VISIBLE_DEVICES=a.gpu_device)
    ehash=digest(engine.read_bytes()); attempt=str(uuid.uuid4()); history=[]; prefix=[]
    if Path(a.checkpoint).exists():
        c=read(a.checkpoint); receipts=read(a.receipt)
        if c.get('manifest_sha256')!=mhash or c.get('engine_sha256')!=ehash or c.get('build')!=a.build or c.get('backend','emulated')!=backend: raise ValueError('Checkpoint provenance differs')
        n=c.get('completed_prefix')
        if type(n) is not int or not 0<=n<=len(manifest['packets']) or len(receipts['receipts'])<n: raise ValueError('Checkpoint prefix invalid')
        if digest(json.dumps(receipts['receipts'][:n],sort_keys=True).encode())!=c['receipt_sha256']: raise ValueError('Checkpoint receipt digest mismatch')
        prefix=receipts['receipts'][:n]; history=receipts['attempts']
        for i,r in enumerate(prefix): check_receipt(r,manifest['packets'][i],i,backend)
    resumed=len(prefix); history.append(attempt); began=time.monotonic()
    total_points=sum(r['points'] for r in manifest['packets'])
    atomic(a.progress,sum(r['points'] for r in manifest['packets'][:resumed])/max(1,total_points))
    print(json.dumps(dict(event='start',attempt=attempt,resumed_prefix=resumed,build=a.build)),flush=True)
    with EngineSession([str(engine)],backend,time.monotonic()+a.max_seconds,environment=engine_environment) as session:
        for i in range(resumed,len(manifest['packets'])):
            row=manifest['packets'][i]; response,elapsed=session.run(row['packet'],timeout=min(120,a.max_seconds))
            verify(row['packet'],response,backend,row['expected'])
            prefix.append(dict(index=i,packet_sha256=row['packet_sha256'],response=response,attempt=attempt,native_seconds=elapsed))
            receipts=dict(receipts=prefix,attempts=history)
            atomic(a.receipt,receipts) # durable receipt BEFORE checkpoint declares progress
            atomic(a.checkpoint,dict(manifest_sha256=mhash,engine_sha256=ehash,build=a.build,backend=backend,completed_prefix=len(prefix),receipt_sha256=digest(json.dumps(prefix,sort_keys=True).encode())))
            atomic(a.progress,sum(r['points'] for r in manifest['packets'][:len(prefix)])/max(1,total_points))
            print(json.dumps(dict(event='committed',attempt=attempt,prefix=len(prefix))),flush=True)
            if a.pause_after==len(prefix): time.sleep(a.pause_seconds)
            if a.fail_after==len(prefix): raise RuntimeError('TEST_ONLY deliberate failed attempt')
            if a.packet_delay: time.sleep(a.packet_delay)
    atomic(a.output,dict(schema='fifth42-boinc-result-v1',TEST_ONLY=True,new_scientific_coverage=False,manifest_sha256=mhash,engine_sha256=ehash,build=a.build,backend=backend,gpu_device_num=a.gpu_device,attempts=history,receipts=prefix,completed_prefix=len(prefix),elapsed_seconds=time.monotonic()-began,resumed_prefix=resumed))
    if a.corrupt_output:
        result=read(a.output)
        if a.corrupt_output=='identity': result['manifest_sha256']='0'*64
        elif a.corrupt_output=='count': result['receipts'][0]['response']['points_visited']+=1
        elif a.corrupt_output=='truncated': result['receipts']=result['receipts'][:-1]
        atomic(a.output,result)
        print(json.dumps(dict(event='TEST_ONLY_corrupt_output',kind=a.corrupt_output)),flush=True)
    print(json.dumps(dict(event='complete',prefix=len(prefix),attempt=attempt)),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--manifest',default='manifest.json'); p.add_argument('--engine',default='scaling_cpu'); p.add_argument('--output',default='result.json'); p.add_argument('--checkpoint',default='checkpoint.json'); p.add_argument('--receipt',default='receipts.json'); p.add_argument('--build',required=True); p.add_argument('--max-seconds',type=int,default=600); p.add_argument('--pause-after',type=int,default=-1); p.add_argument('--pause-seconds',type=int,default=60); p.add_argument('--fail-after',type=int,default=-1)
    p.add_argument('--corrupt-output',choices=['identity','count','truncated'],help='TEST_ONLY server rejection fixture; exits zero')
    p.add_argument('--progress',default='fraction_done.txt');p.add_argument('--packet-delay',type=float,default=0,help='TEST_ONLY checkpoint observation delay')
    p.add_argument('--backend',choices=['cpu','gpu'],default='cpu')
    p.add_argument('--gpu-device',help='BOINC wrapper GPU_DEVICE_NUM; required for GPU execution')
    a=p.parse_args()
    if not 1<=a.max_seconds<=600 or not 0<=a.pause_seconds<=120 or not 0<=a.packet_delay<=5: p.error('Bounded runtime required')
    main(a)
