#!/usr/bin/env python3
"""Server-side science check. Trusted manifest/hash allowlist is NOT uploaded by worker."""
import argparse,json,subprocess
from pathlib import Path
from science_driver import load_manifest,check_receipt
from colab_bench import verify,normalized
from validation_errors import ScientificValidationError, ValidationInfrastructureError

def validate(manifest_path,result_path,gmp,allowed_engine,allowed_build,allowed_backend='emulated'):
    # Trusted server inputs and filesystem access are infrastructure. An invalid
    # server manifest or unreadable upload must not permanently reject a worker.
    m,mhash=load_manifest(manifest_path)
    raw=Path(result_path).read_bytes()
    try:
        result=json.loads(raw)
        if not isinstance(result,dict): raise ValueError('Result must be an object')
        if result.get('schema')!='fifth42-boinc-result-v1' or result.get('TEST_ONLY') is not True or result.get('new_scientific_coverage') is not False: raise ValueError('Result scope/schema')
        if result.get('manifest_sha256')!=mhash or result.get('engine_sha256')!=allowed_engine or result.get('build')!=allowed_build: raise ValueError('Result provenance')
        if result.get('backend','emulated')!=allowed_backend: raise ValueError('Result backend')
        n=result.get('completed_prefix'); receipts=result.get('receipts')
        if type(n) is not int or n!=len(m['packets']) or not isinstance(receipts,list) or len(receipts)!=n: raise ValueError('Incomplete result')
        for i,(r,row) in enumerate(zip(receipts,m['packets'])):
            check_receipt(r,row,i,allowed_backend)
    except (ValueError,KeyError,TypeError,AttributeError,IndexError,OverflowError) as exc:
        raise ScientificValidationError(str(exc)) from exc
    for i,(r,row) in enumerate(zip(receipts,m['packets'])):
        try:
            oracle=subprocess.run([str(Path(gmp).resolve())],input=row['packet'],capture_output=True,text=True,check=True,timeout=120)
            ref=json.loads(oracle.stdout); verify(row['packet'],ref,'emulated',row['expected'])
        except (OSError,subprocess.SubprocessError,ValueError,KeyError,TypeError,AttributeError,IndexError,OverflowError) as exc:
            raise ValidationInfrastructureError('Independent GMP oracle unavailable or invalid') from exc
        if normalized(ref)!=normalized(r['response']): raise ScientificValidationError('Independent GMP differs')
    return dict(scientifically_accepted=True,TEST_ONLY=True,new_scientific_coverage=False,packets=n,positions=sum(r['points'] for r in m['packets']),manifest_sha256=mhash,build=allowed_build)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--result',required=True);p.add_argument('--gmp',required=True);p.add_argument('--engine-sha256',required=True);p.add_argument('--build',required=True);p.add_argument('--backend',choices=['cpu','gpu'],default='cpu');a=p.parse_args()
    print(json.dumps(validate(a.manifest,a.result,a.gmp,a.engine_sha256,a.build,'gpu' if a.backend=='gpu' else 'emulated'),sort_keys=True))
