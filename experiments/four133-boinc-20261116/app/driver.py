"""One CPU, durable completed-task prefix, and exact four133 native receipts."""
import argparse
import ctypes
import json
import math
import os
import resource
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from protocol import (HERE, MAX_CANDIDATES, MAX_LOG_BYTES, SOURCE_SHA, atomic, canonical,
                      load_manifest, read_json, require, sha, task_case)
from audit import validate as audit_log


def allocation(path, standalone=False):
    if not Path(path).exists():
        require(standalone, 'BOINC CPU allocation is required')
        return 'standalone'
    root = ET.parse(path).getroot()
    require(root.tag == 'app_init_data', 'Invalid BOINC init metadata')
    cpus = float(root.findtext('ncpus','nan'))
    require(math.isfinite(cpus) and cpus == 1, 'This application requires exactly one BOINC CPU')
    require(not root.findtext('gpu_type',''), 'CPU application cannot consume a GPU allocation')
    return 'BOINC'


def inspect_log(path, task):
    require(Path(path).stat().st_size <= MAX_LOG_BYTES, 'Native output exceeded bound')
    report = audit_log(path,task['bound'],task['previous_bound'],task_case(task),task['modulus'],
                       task['start'],task['end'],SOURCE_SHA,task['engine_mode']=='synthetic')
    return {key:report[key] for key in ('totals','candidates','exact')}


def parent_guard():
    if sys.platform.startswith('linux'):
        expected = os.getppid()
        libc = ctypes.CDLL(None,use_errno=True)
        if libc.prctl(1,signal.SIGTERM,0,0,0) != 0 or os.getppid() != expected:
            os._exit(126)


def cpu_seconds():
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time() + children.ru_utime + children.ru_stime


def execute(engine, task, path, remaining_cpu):
    command = [str(engine),task['pattern'],str(task['bound']),str(task['previous_bound']),
        str(task['modulus']),str(task['normalized_sum']),str(task['sign']),str(task['start']),
        str(task['end']),SOURCE_SHA,task['engine_mode'],str(MAX_CANDIDATES)]
    child = None
    require(remaining_cpu > 0, 'Bounded application CPU time expired')
    def child_limits():
        parent_guard()
        # Kernel CPU accounting excludes BOINC suspension and duty-cycle waits.
        limit = max(1,math.ceil(remaining_cpu))
        resource.setrlimit(resource.RLIMIT_CPU,(limit,limit))
    with path.open('xb') as output:
        try:
            child = subprocess.Popen(command,stdout=output,stderr=output,
                preexec_fn=child_limits)
            while child.poll() is None:
                require(path.stat().st_size <= MAX_LOG_BYTES, 'Native log exceeded bound')
                time.sleep(.05)
            require(child.returncode == 0, 'Native engine failed; incomplete task retained')
            output.flush()
            os.fsync(output.fileno())
        finally:
            if child is not None and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
    return inspect_log(path,task)


def run(args):
    began = time.monotonic()
    began_cpu = cpu_seconds()
    manifest, identity = load_manifest(args.manifest)
    delivery = allocation(args.init_data,args.standalone)
    engine = Path(args.engine).resolve()
    build = read_json(args.build)
    require(build['source_sha256'] == SOURCE_SHA and build['engine_sha256'] == sha(engine.read_bytes()),
            'Application binary/source identity differs')
    engine_hash = build['engine_sha256']
    checkpoint = Path(args.checkpoint)
    receipts_path = Path(args.receipts)
    records = []
    if checkpoint.exists():
        saved = read_json(checkpoint,65536)
        receipts = read_json(receipts_path)
        require(saved['manifest_sha256'] == identity and saved['engine_sha256'] == engine_hash,
                'Checkpoint work/binary identity changed')
        require(type(saved['completed_tasks']) is int and 0 <= saved['completed_tasks'] <= len(manifest['tasks']),
                'Invalid checkpoint prefix')
        require(isinstance(receipts,list) and len(receipts) >= saved['completed_tasks'], 'Receipt prefix missing')
        records = receipts[:saved['completed_tasks']]
        require(sha(canonical(records)) == saved['receipts_sha256'], 'Durable receipt prefix changed')
        for index, record in enumerate(records):
            require(type(record['task_id']) is int and record['task_id'] == index, 'Receipt task order differs')
            path = Path(record['log_name'])
            require(path.name == f'task-{index:03d}.log' and path.parent == Path('.'), 'Unexpected checkpoint log path')
            require(sha(path.read_bytes()) == record['log_sha256'], 'Committed native log changed')
            require(inspect_log(path,manifest['tasks'][index]) == record['science'], 'Committed native science changed')
    resumed = len(records)
    print(json.dumps(dict(event='start',resumed_tasks=resumed,unit_id=manifest['unit_id'])),flush=True)
    for task in manifest['tasks'][resumed:]:
        index = task['id']
        path = Path(f'task-{index:03d}.log')
        # An interrupted, uncommitted log is preserved and recomputed.
        attempt = 0
        partial = Path(f'task-{index:03d}.attempt-{attempt}.partial')
        while partial.exists():
            attempt += 1
            partial = Path(f'task-{index:03d}.attempt-{attempt}.partial')
        report = execute(engine,task,partial,args.max_seconds-(cpu_seconds()-began_cpu))
        require(cpu_seconds()-began_cpu <= args.max_seconds+1, 'Bounded application CPU time expired')
        os.replace(partial,path)
        fd = os.open(path.parent,os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        records.append(dict(task_id=index,log_name=path.name,log_sha256=sha(path.read_bytes()),science=report))
        atomic(receipts_path,records)
        atomic(checkpoint,dict(manifest_sha256=identity,engine_sha256=engine_hash,
            completed_tasks=len(records),receipts_sha256=sha(canonical(records))))
        Path(args.progress).write_text(str(len(records)/len(manifest['tasks']))+'\n')
        print(json.dumps(dict(event='committed',completed_tasks=len(records))),flush=True)
        if len(records) == manifest['test_pause_after']:
            time.sleep(manifest['test_pause_seconds'])
    result = dict(schema='four133-result-v1',exponent=133,target=42,purpose=manifest['purpose'],
        new_scientific_coverage=False,manifest_sha256=identity,
        engine_sha256=engine_hash,source_sha256=SOURCE_SHA,delivery=delivery,boinc_ncpus=1,
        completed_tasks=len(records),resumed_tasks=resumed,
        records=[dict(task_id=r['task_id'],log=Path(r['log_name']).read_text(),log_sha256=r['log_sha256']) for r in records],
        elapsed_seconds=time.monotonic()-began)
    atomic(args.output,result)
    print(json.dumps(dict(event='complete',completed_tasks=len(records))),flush=True)
    return result


def main():
    def stop(*args):
        raise KeyboardInterrupt('BOINC task interrupted; durable prefix retained')
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest',default='manifest.json')
    parser.add_argument('--engine',default='bin/four133_engine')
    parser.add_argument('--build',default='FOUR133_BUILD.json')
    parser.add_argument('--output',default='result.json')
    parser.add_argument('--checkpoint',default='checkpoint.json')
    parser.add_argument('--receipts',default='receipts.json')
    parser.add_argument('--progress',default='fraction_done.txt')
    parser.add_argument('--init-data',default='init_data.xml')
    parser.add_argument('--standalone',action='store_true')
    parser.add_argument('--max-seconds',type=int,default=300)
    args = parser.parse_args()
    require(1 <= args.max_seconds <= 300, 'Runtime must be bounded to 300 seconds')
    run(args)


if __name__ == '__main__':
    main()
