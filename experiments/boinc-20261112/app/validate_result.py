#!/usr/bin/env python3
"""Server-side science check. Trusted manifest/hash allowlist is NOT uploaded by worker."""
import argparse,json,subprocess
from pathlib import Path
from science_driver import load_manifest,check_receipt
from colab_bench import verify,normalized

def validate(manifest_path,result_path,gmp,allowed_engine,allowed_build):
    m,mhash=load_manifest(manifest_path); result=json.loads(Path(result_path).read_text())
    if result.get('schema')!='fifth42-boinc-result-v1' or result.get('TEST_ONLY') is not True or result.get('new_scientific_coverage') is not False: raise ValueError('Result scope/schema')
    if result.get('manifest_sha256')!=mhash or result.get('engine_sha256')!=allowed_engine or result.get('build')!=allowed_build: raise ValueError('Result provenance')
    n=result.get('completed_prefix'); receipts=result.get('receipts')
    if type(n) is not int or n!=len(m['packets']) or not isinstance(receipts,list) or len(receipts)!=n: raise ValueError('Incomplete result')
    for i,(r,row) in enumerate(zip(receipts,m['packets'])):
        check_receipt(r,row,i)
        oracle=subprocess.run([str(Path(gmp).resolve())],input=row['packet'],capture_output=True,text=True,check=True,timeout=120)
        ref=json.loads(oracle.stdout); verify(row['packet'],ref,'emulated',row['expected'])
        if normalized(ref)!=normalized(r['response']): raise ValueError('Independent GMP differs')
    return dict(scientifically_accepted=True,TEST_ONLY=True,new_scientific_coverage=False,packets=n,positions=sum(r['points'] for r in m['packets']),manifest_sha256=mhash,build=allowed_build)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--result',required=True);p.add_argument('--gmp',required=True);p.add_argument('--engine-sha256',required=True);p.add_argument('--build',required=True);a=p.parse_args()
    print(json.dumps(validate(a.manifest,a.result,a.gmp,a.engine_sha256,a.build),sort_keys=True))
