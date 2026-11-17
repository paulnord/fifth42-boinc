"""Linux CPU/CUDA packages with hash-pinned stock wrapper and bundled Python."""
import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from protocol import atomic, canonical, sha
ASSETS = {
    'wrapper': ('https://github.com/BOINC/boinc/releases/download/wrapper/26019/wrapper_26019_x86_64-pc-linux-gnu',
                '38d3ecc92f314772d0358dff732ca3d98877215d5c470f87b2f13e6760b05fbf'),
    'python.tar.gz': ('https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.13.18%2B20261110-x86_64-unknown-linux-gnu-install_only.tar.gz',
                      '50c774f6674740739f791c05a9177ed03e2fe02abebda9bca3512eb7309b37cc'),
    'libzip.deb': ('https://archive.ubuntu.com/ubuntu/pool/universe/libz/libzip/libzip4t64_1.7.3-1.1ubuntu2_amd64.deb',
                   'd7484efd8d9968ecab9e488fde59980fc633e0eb2bbf7f1ea8e33bf71c9ff1fb')}


def build(dest, backend, assets=None, gpu_engine=None):
    dest = Path(dest).resolve()
    dest.mkdir(exist_ok=False)
    payload = dest / 'payload'
    (payload / 'app').mkdir(parents=True)
    for name in ('protocol.py', 'search.py', 'driver.py'):
        shutil.copy2(ROOT / 'app' / name, payload / 'app' / name)
    if backend == 'gpu':
        if gpu_engine is None:
            raise ValueError('A native tested CUDA engine is required')
        (payload / 'bin').mkdir()
        shutil.copy2(gpu_engine, payload / 'bin/near_gpu')
        (payload / 'bin/near_gpu').chmod(0o755)
    metadata = dict(application='fermat_near', version='1.00' if backend == 'cpu' else '1.10', platform='x86_64-pc-linux-gnu',
        backend=backend, boinc_ncpus=1, gpu=(backend == 'gpu'),
        cuda_source_sha256=sha((ROOT / 'native/near_gpu.cu').read_bytes()) if backend == 'gpu' else None,
        files={str(p.relative_to(payload)): sha(p.read_bytes()) for p in sorted(payload.rglob('*')) if p.is_file()})
    atomic(payload / 'NEAR_BUILD.json', metadata)
    for name, (url, expected) in ASSETS.items():
        cached = Path(assets) / name if assets else None
        data = cached.read_bytes() if cached and cached.exists() else urllib.request.urlopen(url, timeout=120).read()
        if sha(data) != expected:
            raise ValueError('Changed upstream asset: ' + name)
        (dest / name).write_bytes(data)
    (dest / 'wrapper').chmod(0o755)
    subprocess.run(['dpkg-deb', '-x', str(dest / 'libzip.deb'), str(dest / 'zip-input')], check=True)
    shutil.copy2(dest / 'zip-input/usr/lib/x86_64-linux-gnu/libzip.so.4.0', dest / 'libzip.so.4')
    shutil.copy2(dest / 'zip-input/usr/share/doc/libzip4t64/copyright', dest / 'libzip-COPYRIGHT.txt')
    with tarfile.open(dest / 'python.tar.gz') as archive:
        archive.extractall(dest / 'python-input', filter='data')
    with zipfile.ZipFile(dest / 'runtime.zip', 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for directory, prefix in [(dest / 'python-input/python', 'python/'), (payload, '')]:
            for p in sorted(directory.rglob('*')):
                if p.is_dir():
                    continue
                if not p.is_file() or not p.resolve().is_relative_to(directory.resolve()):
                    raise ValueError('Unsafe runtime member')
                info = zipfile.ZipInfo(prefix + str(p.relative_to(directory)))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | (p.stat().st_mode & 0o777)) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, p.read_bytes())
    gpu = ' --gpu-device $GPU_DEVICE_NUM' if backend == 'gpu' else ''
    (dest / 'job.xml').write_text(f'''<job_desc>
<unzip_input><zipfilename>runtime.zip</zipfilename></unzip_input>
<task><application>python/bin/python3.13</application>
<command_line>-s app/driver.py --backend {backend}{gpu} --manifest boinc_resolve(manifest.json) --output boinc_resolve(result.json)</command_line>
<setenv>PYTHONHOME=$PWD/python</setenv><multi_process/>
<checkpoint_filename>checkpoint.json</checkpoint_filename><fraction_done_filename>fraction_done.txt</fraction_done_filename>
<stdout_filename>near.stdout</stdout_filename><stderr_filename>near.stderr</stderr_filename></task>
</job_desc>
''')
    files = ['wrapper', 'runtime.zip', 'job.xml', 'libzip.so.4', 'libzip-COPYRIGHT.txt']
    package = dict(metadata, build_identity=sha(canonical(metadata)), plan_class='fermat_near_' + backend + '_1',
                   client_files=files, source_files=metadata['files'],
                   assets={k: dict(url=v[0], sha256=v[1]) for k, v in ASSETS.items()},
                   files={name: sha((dest / name).read_bytes()) for name in files})
    atomic(dest / 'BOINC_BUILD.json', package)
    print(json.dumps(dict(package=str(dest), backend=backend, build_identity=package['build_identity'])), flush=True)
    return dest


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('destination')
    p.add_argument('--backend', choices=['cpu', 'gpu'], required=True)
    p.add_argument('--assets', help='Optional cache of the pinned wrapper, Python archive, libzip.deb')
    p.add_argument('--gpu-engine')
    a = p.parse_args()
    build(a.destination, a.backend, a.assets, a.gpu_engine)
