"""Full GMP replay of each assigned region; worker claims cannot select work."""
import json
import math
import subprocess
from pathlib import Path
from protocol import canonical, checks, load_manifest, read, require, sha


class InfrastructureUnavailable(RuntimeError):
    pass


def oracle(task, executable):
    try:
        result = subprocess.run([str(executable), *map(str, (task['exponent'], task['first_c'],
            task['last_c'], task['k_num'], task['k_den']))], capture_output=True, text=True,
            check=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise InfrastructureUnavailable('Independent GMP replay unavailable') from exc
    hits, done = [], None
    for line in result.stdout.splitlines():
        fields = line.split()
        if fields[0] == 'H' and len(fields) == 5:
            hits.append([int(fields[1]), int(fields[2]), int(fields[3]), str(int(fields[4]))])
        elif fields[0] == 'DONE' and len(fields) == 3 and done is None:
            done = list(map(int, fields[1:]))
        else:
            raise InfrastructureUnavailable('Malformed GMP replay output')
    if done != [checks(task), len(hits)]:
        raise InfrastructureUnavailable('Incomplete independent enumeration')
    return dict(hits=sorted(hits, key=lambda h: (h[2], h[0], h[1])), a_values=checks(task))


def validate(manifest_path, result_path, executable, build_identity, backend, delivery='BOINC'):
    manifest, identity = load_manifest(manifest_path)
    result = read(result_path)
    require(isinstance(result, dict) and set(result) == {'schema', 'purpose', 'new_scientific_coverage',
        'manifest_sha256', 'build_identity', 'backend', 'delivery', 'gpu_device', 'boinc_ncpus',
        'completed_tasks', 'resumed_tasks', 'records', 'elapsed_seconds'}, 'Result fields differ')
    require(result['schema'] == 'fermat-near-result-v1' and result['purpose'] == 'TEST_ONLY'
            and result['new_scientific_coverage'] is False, 'Result scope differs')
    require(result['manifest_sha256'] == identity and result['build_identity'] == build_identity,
            'Untrusted work or build identity')
    require(result['backend'] == backend and result['delivery'] == delivery
            and type(result['boinc_ncpus']) is int and result['boinc_ncpus'] == 1, 'Delivery/backend differs')
    require(isinstance(result['records'], list), 'Result chunk list required')
    device = result['gpu_device']
    require((backend == 'cpu' and device is None) or (backend in ('gpu', 'metal') and isinstance(device, str)
            and device.isascii() and device.isdecimal()), 'GPU allocation receipt differs')
    require(type(result['completed_tasks']) is int and result['completed_tasks'] == len(manifest['tasks'])
            and len(result['records']) == len(manifest['tasks']), 'Incomplete work')
    require(type(result['resumed_tasks']) is int and 0 <= result['resumed_tasks'] <= len(manifest['tasks']),
            'Invalid resumed prefix')
    hits = primitive = total = 0
    per_exponent = {}
    for task, record in zip(manifest['tasks'], result['records']):
        require(isinstance(record, dict) and set(record) == {'task', 'science'}, 'Chunk fields differ')
        require(record['task'] == task, 'Chunk assignment differs')
        expected = oracle(task, executable)
        # Canonical bytes also reject floats/bools masquerading as integer values.
        require(canonical(record['science']) == canonical(expected), 'GMP enumeration differs or candidates omitted')
        hits += len(expected['hits'])
        primitive += sum(math.gcd(a, b, c) == 1 for a, b, c, _ in expected['hits'])
        total += expected['a_values']
        per_exponent[str(task['exponent'])] = per_exponent.get(str(task['exponent']), 0) + len(expected['hits'])
    return dict(scientifically_accepted=True, purpose='TEST_ONLY', new_scientific_coverage=False,
        manifest_sha256=identity, result_sha256=sha(Path(result_path).read_bytes()),
        backend=backend, completed_tasks=result['completed_tasks'], resumed_tasks=result['resumed_tasks'],
        independently_enumerated_a_values=total, GMP_verified_candidates=hits,
        primitive_candidates=primitive, candidates_by_exponent=per_exponent,
        accounting='Complete assigned c rows only; bounded client acceptance, no campaign coverage')
