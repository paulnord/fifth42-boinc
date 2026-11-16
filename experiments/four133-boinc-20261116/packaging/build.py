"""Build native four133, then bundle pinned BOINC wrapper and CPython runtime."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from protocol import SOURCE_SHA, make_controls, sha

PINS = {
 'linux-x86_64': dict(platform='x86_64-pc-linux-gnu',
    wrapper_url='https://github.com/BOINC/boinc/releases/download/wrapper/26019/wrapper_26019_x86_64-pc-linux-gnu',
    wrapper_sha256='38d3ecc92f314772d0358dff732ca3d98877215d5c470f87b2f13e6760b05fbf',
    python_url='https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.13.18%2B20261110-x86_64-unknown-linux-gnu-install_only.tar.gz',
    python_sha256='50c774f6674740739f791c05a9177ed03e2fe02abebda9bca3512eb7309b37cc'),
 'macos-arm64': dict(platform='arm64-apple-darwin',
    wrapper_url='https://github.com/BOINC/boinc/releases/download/wrapper/26019/wrapper_26019_universal-apple-darwin',
    wrapper_sha256='d2d08516ced84527e658a366585d76f1cae2017dd0c07a00a5dc9e883968ed59',
    python_url='https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.13.18%2B20261110-aarch64-apple-darwin-install_only.tar.gz',
    python_sha256='1afd3983237c2a10277345f235be730e9cb49a123e0574ed252dbf3a841a24e4')}


def fetch(url,digest,dest):
    data = urllib.request.urlopen(url,timeout=120).read()
    if sha(data) != digest:
        raise ValueError('Pinned upstream asset changed: '+dest.name)
    dest.write_bytes(data)


def build(destination,compiler):
    dest = Path(destination).resolve()
    dest.mkdir(exist_ok=False)
    native = 'macos-arm64' if platform.system() == 'Darwin' and platform.machine() == 'arm64' else 'linux-x86_64'
    if native == 'linux-x86_64' and not (platform.system() == 'Linux' and platform.machine() == 'x86_64'):
        raise ValueError('Only Linux x86_64 and Apple Silicon are packaged')
    pin = PINS[native]
    runtime = dest/'payload'
    (runtime/'bin').mkdir(parents=True)
    shutil.copytree(ROOT/'app',runtime/'app',ignore=shutil.ignore_patterns('__pycache__','*.cpp'))
    shutil.copytree(ROOT/'upstream',runtime/'upstream',ignore=shutil.ignore_patterns('__pycache__','tests'))
    if sha((ROOT/'upstream/src/search.cpp').read_bytes()) != SOURCE_SHA:
        raise ValueError('Frozen upstream source changed')
    common = [compiler,'-O3','-std=c++17','-Wall','-Wextra','-Werror']
    flags = ['-static-libstdc++','-static-libgcc'] if native == 'linux-x86_64' else []
    # The immutable upstream join loop triggers Clang's indentation warning.
    # Keep its bytes/provenance intact, while retaining all other error checks.
    upstream_flags = ['-Wno-misleading-indentation'] if native == 'macos-arm64' else []
    subprocess.run(common+flags+upstream_flags+[str(ROOT/'upstream/src/search.cpp'),'-o',str(runtime/'bin/four133_engine')],check=True)
    gmp_flags=[]
    if native == 'macos-arm64':
        prefix=subprocess.check_output(['brew','--prefix','gmp'],text=True).strip()
        gmp_flags=['-I'+prefix+'/include','-L'+prefix+'/lib']
    subprocess.run(common+flags+gmp_flags+[str(ROOT/'app/gmp_exact.cpp'),'-lgmpxx','-lgmp','-o',str(dest/'gmp_exact')],check=True)
    metadata=dict(schema='four133-build-v1',application='four133',version='1.00',platform=pin['platform'],
        source_sha256=SOURCE_SHA,upstream=json.loads((ROOT/'UPSTREAM.json').read_text()),
        engine_sha256=sha((runtime/'bin/four133_engine').read_bytes()),
        cpu_budget=1,gpu=False,compiler=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],
        files={str(p.relative_to(runtime)):sha(p.read_bytes()) for p in sorted(runtime.rglob('*')) if p.is_file()})
    (runtime/'FOUR133_BUILD.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (dest/'controls.json').write_text(json.dumps(make_controls(),indent=2)+'\n')
    print('Native four133 and independent GMP checker built; fetching pinned runtime.',flush=True)
    fetch(pin['wrapper_url'],pin['wrapper_sha256'],dest/'wrapper')
    (dest/'wrapper').chmod(0o755)
    archive=dest/'python.tar.gz'
    fetch(pin['python_url'],pin['python_sha256'],archive)
    with tarfile.open(archive,'r:gz') as t:
        t.extractall(dest/'python-input',filter='data')
    python=dest/'python-input/python'
    with zipfile.ZipFile(dest/'runtime.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for directory,prefix in [(python,'python/'),(runtime,'')]:
            for f in sorted(directory.rglob('*')):
                if f.is_dir():
                    continue
                if not f.is_file() or not f.resolve().is_relative_to(directory.resolve()):
                    raise ValueError('Unsafe runtime member: '+str(f))
                info=zipfile.ZipInfo(prefix+str(f.relative_to(directory)))
                info.create_system=3
                info.external_attr=(stat.S_IFREG | (f.stat().st_mode&0o777))<<16
                info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,f.read_bytes())
    job='''<job_desc>
<unzip_input><zipfilename>runtime.zip</zipfilename></unzip_input>
<task>
<application>python/bin/python3.13</application>
<command_line>-s app/driver.py --manifest boinc_resolve(manifest.json) --output boinc_resolve(result.json)</command_line>
<setenv>PYTHONHOME=$PWD/python</setenv>
<multi_process/>
<checkpoint_filename>checkpoint.json</checkpoint_filename>
<fraction_done_filename>fraction_done.txt</fraction_done_filename>
<stdout_filename>four133.stdout</stdout_filename>
<stderr_filename>four133.stderr</stderr_filename>
</task>
</job_desc>
'''
    (dest/'job.xml').write_text(job)
    package=dict(metadata,upstream_assets=pin,
        runtime_unpacked_bytes=sum(i.file_size for i in zipfile.ZipFile(dest/'runtime.zip').infolist()),
        files={name:sha((dest/name).read_bytes()) for name in ('wrapper','runtime.zip','job.xml','controls.json')})
    (dest/'BOINC_BUILD.json').write_text(json.dumps(package,indent=2)+'\n')
    with tarfile.open(dest/'four133-boinc.tar.gz','x:gz') as t:
        for filename in ['wrapper','runtime.zip','job.xml','controls.json','BOINC_BUILD.json']:
            t.add(dest/filename,arcname='four133-boinc/'+filename)
    print(json.dumps(dict(platform=pin['platform'],engine_sha256=metadata['engine_sha256'],package=str(dest/'four133-boinc.tar.gz')),indent=2))
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('destination')
    p.add_argument('--compiler',default='clang++' if sys.platform=='darwin' else 'g++')
    a=p.parse_args()
    build(a.destination,a.compiler)
