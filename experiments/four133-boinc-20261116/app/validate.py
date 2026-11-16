"""Server validation replays all modular joins and checks final powers with GMP."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import subprocess
import tempfile

from driver import inspect_log
from protocol import MAX_LOG_BYTES, SOURCE_SHA, canonical, load_manifest, read_json, require, sha
from reference import reference


class InfrastructureUnavailable(RuntimeError):
    pass


def validate(manifest_path,result_path,gmp_path,expected_engine,expected_delivery=None):
    manifest, identity = load_manifest(manifest_path)
    result = read_json(result_path)
    require(isinstance(result,dict) and result.get('schema') == 'four133-result-v1', 'Result schema differs')
    require(type(result.get('exponent')) is int and result['exponent'] == 133 and type(result.get('target')) is int
            and result['target'] == 42, 'Result equation differs')
    require(result.get('manifest_sha256') == identity and result.get('source_sha256') == SOURCE_SHA
            and result.get('engine_sha256') == expected_engine, 'Result provenance differs')
    require(result.get('purpose') == manifest['purpose'] and result.get('new_scientific_coverage') is False,
            'Coverage scope differs')
    require(result.get('delivery') in ('BOINC','standalone') and type(result.get('boinc_ncpus')) is int
            and result['boinc_ncpus'] == 1, 'CPU allocation receipt differs')
    if expected_delivery is not None:
        require(result['delivery'] == expected_delivery, 'Delivery contract differs')
    require(type(result.get('completed_tasks')) is int and result['completed_tasks'] == len(manifest['tasks']), 'Incomplete task coverage')
    require(type(result.get('resumed_tasks')) is int and 0 <= result['resumed_tasks'] <= len(manifest['tasks']), 'Invalid resume receipt')
    require(type(result.get('elapsed_seconds')) in (int,float) and math.isfinite(result['elapsed_seconds'])
            and result['elapsed_seconds'] >= 0, 'Invalid elapsed time')
    records = result.get('records')
    require(isinstance(records,list) and len(records) == len(manifest['tasks']), 'Missing/duplicate task receipts')
    reports = []
    exact = set()
    native_controls = 0
    with tempfile.TemporaryDirectory() as directory:
        for index,(task,record) in enumerate(zip(manifest['tasks'],records)):
            require(isinstance(record,dict) and set(record) == {'task_id','log','log_sha256'}, 'Native receipt fields differ')
            require(type(record['task_id']) is int and record['task_id'] == index, 'Duplicate/reordered task receipt')
            require(isinstance(record['log'],str) and len(record['log'].encode()) <= MAX_LOG_BYTES, 'Native log exceeds bound')
            require(sha(record['log'].encode()) == record['log_sha256'], 'Native log hash differs')
            path = Path(directory)/'task.log'
            path.write_text(record['log'])
            try:
                report = inspect_log(path,task)
            except (AssertionError,KeyError,IndexError,TypeError,OverflowError) as exc:
                raise ValueError('Invalid native log: '+str(exc)) from exc
            rows,wanted = reference(task)
            checkpoints = [line for line in record['log'].splitlines() if line.startswith('CHECKPOINT ')]
            from audit import fields
            for checkpoint,expected in zip(checkpoints,rows):
                actual = fields(checkpoint)
                require(all(int(actual[k]) == value for k,value in expected.items()), 'Independent join/count mismatch')
            require(len(checkpoints) == len(rows), 'Independent gap coverage differs')
            actual = sorted((x['h'],tuple(x['bases']),x['distinct']) for x in report['candidates'])
            require(actual == wanted, 'Independent modular candidates differ, omitted or forged')
            candidates = report['candidates']
            try:
                run = subprocess.run([str(Path(gmp_path).resolve())],
                    input=''.join(' '.join(map(str,x['bases']))+'\n' for x in candidates),
                    capture_output=True,text=True,check=True,timeout=60)
                residuals = run.stdout.splitlines()
                if len(residuals) != len(candidates):
                    raise InfrastructureUnavailable('Independent GMP output incomplete')
                for candidate,residual in zip(candidates,residuals):
                    if residual != candidate['residual']:
                        raise InfrastructureUnavailable('Independent GMP arithmetic disagreed with Python')
                    if residual == '0':
                        exact.add(tuple(candidate['bases']))
            except (OSError,subprocess.SubprocessError) as exc:
                raise InfrastructureUnavailable('Independent GMP checker unavailable') from exc
            native_controls += len(candidates)
            reports.append(dict(task_id=index,totals=report['totals'],modular_candidates=len(candidates),
                independently_replayed=True,gaps=len(rows),log_sha256=record['log_sha256']))
    return dict(scientifically_accepted=True,exponent=133,target=42,purpose=manifest['purpose'],
        new_scientific_coverage=False,manifest_sha256=identity,
        result_sha256=sha(Path(result_path).read_bytes()),engine_sha256=expected_engine,
        tasks=reports,GMP_candidate_checks=native_controls,exact_hits=sorted(exact),
        accounting='Complete assigned gap regions only; no full-box claim')


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',required=True)
    p.add_argument('--result',required=True)
    p.add_argument('--gmp',required=True)
    p.add_argument('--engine-sha256',required=True)
    p.add_argument('--delivery',choices=['BOINC','standalone'])
    a=p.parse_args()
    print(json.dumps(validate(a.manifest,a.result,a.gmp,a.engine_sha256,a.delivery),indent=2))
