"""One BOINC CPU, optional allocated CUDA GPU, and durable chunk recovery."""
import argparse
import math
import resource
import signal
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from protocol import atomic, canonical, load_manifest, read, require, sha
from search import cpu, gpu


def allocation(path, backend, device, standalone=False):
    if not Path(path).exists():
        require(standalone, 'BOINC allocation required')
        require(backend == 'cpu' or (device is not None and device.isdecimal()), 'CUDA device required')
        return 'standalone'
    root = ET.parse(path).getroot()
    require(root.tag == 'app_init_data', 'BOINC init metadata')
    require(float(root.findtext('ncpus', 'nan')) == 1, 'Exactly one BOINC CPU required')
    kind = root.findtext('gpu_type', '').lower()
    if backend == 'cpu':
        require(not kind, 'CPU package received GPU allocation')
    else:
        require(kind in ('nvidia', 'cuda'), 'BOINC NVIDIA allocation required')
        require(device is not None and device.isascii() and device.isdecimal(), 'Allocated GPU number required')
        recorded = root.findtext('gpu_device_num')
        require(recorded is None or recorded == device, 'Inconsistent GPU allocation')
    return 'BOINC'


def main(args):
    started = time.monotonic()
    initial_cpu = time.process_time()
    def budget():
        child = resource.getrusage(resource.RUSAGE_CHILDREN)
        require(time.process_time() - initial_cpu + child.ru_utime + child.ru_stime <= 300,
                'Application CPU budget exceeded')
    manifest, identity = load_manifest(args.manifest)
    build = read('NEAR_BUILD.json', 65536)
    require(build['backend'] == args.backend, 'Package backend mismatch')
    build_identity = sha(canonical(build))
    for name, digest in build['files'].items():
        require(sha(Path(name).read_bytes()) == digest, 'Changed application file: ' + name)
    delivery = allocation('init_data.xml', args.backend, args.gpu_device, args.standalone)
    records = []
    if Path('checkpoint.json').exists():
        saved = read('checkpoint.json', 65536)
        require(saved['manifest_sha256'] == identity and saved['build_identity'] == build_identity,
                'Checkpoint work or build changed')
        count = saved['completed_tasks']
        require(type(count) is int and 0 <= count <= len(manifest['tasks']), 'Checkpoint prefix bound')
        for index in range(count):
            chunk = read(f'chunk-{index:03d}.json')
            require(chunk['task'] == manifest['tasks'][index], 'Checkpoint chunk identity')
            records.append(chunk)
        require(sha(canonical(records)) == saved['records_sha256'], 'Changed checkpoint prefix')
    resumed = len(records)
    print(canonical(dict(event='start', resumed_tasks=resumed, backend=args.backend)).decode(), flush=True)
    for task in manifest['tasks'][resumed:]:
        budget()
        if args.backend == 'cpu':
            science = cpu(task, budget)
        else:
            science = gpu(task, args.gpu_device, 'bin/near_gpu', f"task-{task['id']:03d}")
        chunk = dict(task=task, science=science)
        records.append(chunk)
        require(len(canonical(records)) <= 6 * 1024 * 1024, 'Output budget exceeded')
        atomic(f"chunk-{task['id']:03d}.json", chunk)
        atomic('checkpoint.json', dict(manifest_sha256=identity, build_identity=build_identity,
            completed_tasks=len(records), records_sha256=sha(canonical(records))))
        Path('fraction_done.txt').write_text(str(len(records) / len(manifest['tasks'])) + '\n')
        print(canonical(dict(event='committed', completed_tasks=len(records))).decode(), flush=True)
        if len(records) == manifest['pause_after']:
            time.sleep(manifest['pause_seconds'])
    budget()
    value = dict(schema='fermat-near-result-v1', purpose='TEST_ONLY', new_scientific_coverage=False,
        manifest_sha256=identity, build_identity=build_identity, backend=args.backend,
        delivery=delivery, gpu_device=args.gpu_device, boinc_ncpus=1,
        completed_tasks=len(records), resumed_tasks=resumed, records=records,
        elapsed_seconds=time.monotonic() - started)
    atomic(args.output, value)
    print(canonical(dict(event='complete', completed_tasks=len(records))).decode(), flush=True)


if __name__ == '__main__':
    def stop(*_):
        raise KeyboardInterrupt('BOINC interruption; durable prefix retained')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', default='manifest.json')
    parser.add_argument('--output', default='result.json')
    parser.add_argument('--backend', choices=['cpu', 'gpu'], required=True)
    parser.add_argument('--gpu-device')
    parser.add_argument('--standalone', action='store_true')
    main(parser.parse_args())
