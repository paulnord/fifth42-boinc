"""Fixed equation, bounded manifests, and immutable four133 application identity."""
import hashlib
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'upstream'))
from math133 import Case, D, MODULI, counts, max_gap

SOURCE_SHA = '46c7824e38320f6dbe2e844a80d1edcf7e489fe61b9124936563953e1f58bc32'
MAX_ENTRIES = 2_000_000
MAX_LOG_BYTES = 4 * 1024 * 1024
MAX_TASKS = 8
MAX_CANDIDATES = 20000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def read_json(path, limit=64*1024*1024):
    require(Path(path).stat().st_size <= limit, 'JSON file exceeds bound')
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, 'Duplicate JSON field')
            result[k] = v
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def atomic(path, value):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('wb') as stream:
        stream.write(canonical(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def task_case(task):
    return Case(task['pattern'], task['normalized_sum'], task['sign'],
                max_gap(task['bound'], task['normalized_sum'], task['sign'], task['pattern']))


def validate_manifest(manifest):
    require(sys.flags.optimize == 0, 'Run without Python optimization: upstream exact guards required')
    require(isinstance(manifest, dict), 'Manifest object required')
    require(set(manifest) == {'schema','exponent','target','purpose','unit_id','source_sha256',
                             'tasks','test_pause_after','test_pause_seconds'}, 'Manifest fields differ')
    require(manifest['schema'] == 'four133-work-v1', 'Wrong work schema')
    require(type(manifest['exponent']) is int and manifest['exponent'] == 133, 'Exponent must be 133')
    require(type(manifest['target']) is int and manifest['target'] == 42, 'Target must be 42')
    require(manifest['source_sha256'] == SOURCE_SHA, 'Unrecognized science source')
    require(manifest['purpose'] in ('TEST_ONLY', 'SEARCH'), 'Explicit purpose required')
    require(isinstance(manifest['unit_id'], str) and 1 <= len(manifest['unit_id']) <= 100
            and all(c.isascii() and (c.isalnum() or c in '_-') for c in manifest['unit_id']), 'Unsafe unit identity')
    tasks = manifest['tasks']
    require(isinstance(tasks, list) and 1 <= len(tasks) <= MAX_TASKS, 'Bounded task list required')
    require(type(manifest['test_pause_after']) is int and 0 <= manifest['test_pause_after'] <= len(tasks), 'Invalid test pause')
    require(type(manifest['test_pause_seconds']) is int and 0 <= manifest['test_pause_seconds'] <= 120, 'Invalid pause duration')
    require(manifest['purpose'] == 'TEST_ONLY' or not manifest['test_pause_after'], 'Search work cannot pause for tests')
    entries = 0
    keys = set()
    for index, task in enumerate(tasks):
        require(isinstance(task, dict) and set(task) == {'id','pattern','bound','previous_bound','normalized_sum',
                'sign','start','end','modulus','engine_mode'}, 'Task fields differ')
        for key in ('id','bound','previous_bound','normalized_sum','sign','start','end','modulus'):
            require(type(task[key]) is int, 'Strict integer task field required: ' + key)
        require(task['id'] == index, 'Ordered task identity required')
        B, old, S, sign, m = (task[k] for k in ('bound','previous_bound','normalized_sum','sign','modulus'))
        require(task['pattern'] in ('22','31') and sign in (-1,1), 'Unknown normalized branch')
        require(44 <= B <= 20000000 and 0 <= old < B and 42 <= S <= 2*B+42, 'Native domain guard')
        require(task['engine_mode'] in ('production','synthetic') and 42 < m < 2**61, 'Native sieve guard')
        if task['engine_mode'] == 'production':
            require(old == 4000000 and m in MODULI and (sign*S-42) % D == 0
                    and -2*B <= sign*S <= 2*B+42, 'Production mathematical constraints differ')
        require(manifest['purpose'] == 'TEST_ONLY' or task['engine_mode'] == 'production', 'Synthetic search coverage forbidden')
        case = task_case(task)
        require(1 <= task['start'] <= task['end'] <= case.H and task['end']-task['start'] < 16, 'Gap interval exceeds bounds')
        key = tuple(task[k] for k in ('pattern','bound','previous_bound','normalized_sum','sign','start','end','modulus'))
        require(key not in keys, 'Duplicate task')
        keys.add(key)
        entries += sum(sum(counts(B,old,case,h)) for h in range(task['start'],task['end']+1))
        require(entries <= MAX_ENTRIES, 'Work unit exceeds pair-entry budget')
    if manifest['purpose'] == 'SEARCH':
        regions = {}
        for task in tasks:
            key = tuple(task[k] for k in ('pattern','bound','previous_bound','normalized_sum','sign','start','end'))
            regions.setdefault(key, set()).add(task['modulus'])
        require(all(moduli == set(MODULI) for moduli in regions.values()), 'Search regions require both independent sieve moduli')
    return entries


def load_manifest(path):
    raw = Path(path).read_bytes()
    require(len(raw) <= 65536, 'Manifest exceeds input bound')
    manifest = read_json(path, 65536)
    validate_manifest(manifest)
    return manifest, sha(raw)


def make_controls():
    tasks = []
    for pattern, B, old, S, sign in [('22',400,0,42,1), ('22',400,200,100,-1),
                                   ('31',1000,0,600,1), ('31',1000,500,600,-1)]:
        tasks.append(dict(id=len(tasks), pattern=pattern, bound=B, previous_bound=old,
            normalized_sum=S, sign=sign, start=1, end=min(4,max_gap(B,S,sign,pattern)),
            modulus=43, engine_mode='synthetic'))
    value = dict(schema='four133-work-v1', exponent=133, target=42, purpose='TEST_ONLY',
        unit_id='four133-controls', source_sha256=SOURCE_SHA, tasks=tasks,
        test_pause_after=0, test_pause_seconds=0)
    validate_manifest(value)
    return value
