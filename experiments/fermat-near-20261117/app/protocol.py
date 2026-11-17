"""Exact bounded Fermat near-miss work, shared by delivery and validation."""
import hashlib
import json
import os
from pathlib import Path

APPLICATION = 'fermat_near'
MAX_C = 20000
MAX_CHECKS = 2000000
MAX_HITS = 20000
MAX_BYTES = 8 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path, limit=MAX_BYTES):
    raw = Path(path).read_bytes()
    require(len(raw) <= limit, 'JSON exceeds size bound')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'Duplicate JSON field')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False, 'Nonfinite JSON'))


def atomic(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('wb') as stream:
        stream.write(canonical(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        move=ctypes.WinDLL('kernel32',use_last_error=True).MoveFileExW
        move.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD]
        move.restype=wintypes.BOOL
        if not move(str(temporary.resolve()),str(path.resolve()),0x1|0x8):
            raise ctypes.WinError(ctypes.get_last_error())
        return
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def checks(task):
    lo, hi = task['first_c'], task['last_c']
    return (hi * (hi - 1) - (lo - 1) * (lo - 2)) // 2


def validate_manifest(value):
    require(set(value) == {'schema', 'purpose', 'unit_id', 'tasks',
                           'pause_after', 'pause_seconds'}, 'Work fields differ')
    require(value['schema'] == 'fermat-near-work-v1' and value['purpose'] == 'TEST_ONLY',
            'Only bounded TEST_ONLY work is admitted')
    name = value['unit_id']
    require(isinstance(name, str) and 1 <= len(name) <= 100 and
            all(c.isascii() and (c.isalnum() or c in '_-') for c in name), 'Unsafe work name')
    tasks = value['tasks']
    require(isinstance(tasks, list) and 1 <= len(tasks) <= 32, 'Bounded chunks required')
    require(type(value['pause_after']) is int and 0 <= value['pause_after'] <= len(tasks), 'Pause index')
    require(type(value['pause_seconds']) is int and 0 <= value['pause_seconds'] <= 120, 'Pause duration')
    regions = {}
    for index, task in enumerate(tasks):
        require(set(task) == {'id', 'exponent', 'first_c', 'last_c', 'k_num', 'k_den'}, 'Chunk fields')
        require(all(type(v) is int for v in task.values()), 'Strict integer chunk fields required')
        require(task['id'] == index and 4 <= task['exponent'] <= 32, 'Exponent or chunk order')
        require(2 <= task['first_c'] <= task['last_c'] <= MAX_C and
                task['last_c'] - task['first_c'] < 256, 'Chunk interval bound')
        require(1 <= task['k_num'] <= 1000000000 and 1 <= task['k_den'] <= 1000000000, 'Cutoff bound')
        key = (task['exponent'], task['k_num'], task['k_den'])
        for lo, hi in regions.setdefault(key, []):
            require(task['last_c'] < lo or task['first_c'] > hi, 'Overlapping chunks')
        regions[key].append((task['first_c'], task['last_c']))
    require(sum(map(checks, tasks)) <= MAX_CHECKS, 'Work exceeds CPU/GPU comparison budget')
    return value


def load_manifest(path):
    value = read(path, 65536)
    validate_manifest(value)
    return value, sha(Path(path).read_bytes())
