"""Package pinned native CPU kit + stock wrapper + relocatable Python for BOINC."""
import argparse,hashlib,io,json,os,shutil,stat,tarfile,urllib.request,zipfile
from pathlib import Path

PINNED_KIT_SHA256='34bd4042a6e33eccf90bc15b396a907045e7312d73a14121affce57095a0d823'
WRAPPER_URL='https://github.com/BOINC/boinc/releases/download/wrapper/26019/wrapper_26019_universal-apple-darwin'
WRAPPER_SHA256='d2d08516ced84527e658a366585d76f1cae2017dd0c07a00a5dc9e883968ed59'
PYTHON_URL='https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.13.18%2B20261110-aarch64-apple-darwin-install_only.tar.gz'
PYTHON_SHA256='1afd3983237c2a10277345f235be730e9cb49a123e0574ed252dbf3a841a24e4'

def sha(data):return hashlib.sha256(data).hexdigest()
def fetch(url,digest,path):
    data=urllib.request.urlopen(url,timeout=120).read()
    if sha(data)!=digest:raise ValueError('Pinned download hash differs: '+path.name)
    path.write_bytes(data);return data

def package(kit_archive,destination):
    base=Path(destination).resolve();base.mkdir(exist_ok=False);inputs=base/'inputs';inputs.mkdir()
    data=Path(kit_archive).read_bytes()
    if sha(data)!=PINNED_KIT_SHA256:raise ValueError('CPU kit archive identity differs')
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:t.extractall(inputs,filter='data')
    kit=inputs/'client-kit';build=json.loads((kit/'BUILD.json').read_text())
    assert build['architecture']=='arm64' and build['TEST_ONLY'] is True
    for name,digest in build['files'].items():assert sha((kit/name).read_bytes())==digest,name
    evidence=json.loads((kit/'NATIVE_TEST_EVIDENCE.json').read_text())
    assert evidence['status']=='passed' and evidence['fresh_local_gmp_all_packets'] is True
    wrapper=base/'wrapper';fetch(WRAPPER_URL,WRAPPER_SHA256,wrapper);wrapper.chmod(0o755)
    python_archive=inputs/'python.tar.gz';fetch(PYTHON_URL,PYTHON_SHA256,python_archive)
    with tarfile.open(python_archive,'r:gz') as t:t.extractall(inputs/'python-runtime',filter='data')
    runtime=inputs/'python-runtime/python';assert (runtime/'bin/python3.13').exists()
    payload=base/'runtime.zip'
    with zipfile.ZipFile(payload,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        # BOINC's stock libzip extractor restores POSIX modes but not symlinks.
        # Materialize internal file links so the runtime remains relocatable.
        for f in sorted(runtime.rglob('*')):
            if f.is_dir():continue
            resolved=f.resolve();assert resolved.is_relative_to(runtime.resolve()),str(f)
            if not f.is_file():raise ValueError('Unexpected runtime entry')
            info=zipfile.ZipInfo('python/'+str(f.relative_to(runtime)));info.create_system=3
            info.external_attr=(stat.S_IFREG | (f.stat().st_mode&0o777))<<16;info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,f.read_bytes())
        for f in sorted((kit/'app').glob('*.py')):
            z.write(f,'app/'+f.name)
        z.write(kit/'bin/scaling_cpu','bin/scaling_cpu')
        z.write(kit/'controls.json','controls.json')
        z.write(kit/'BUILD.json','CPU_BUILD.json');z.write(kit/'NATIVE_TEST_EVIDENCE.json','CPU_GMP_EVIDENCE.json')
    job='''<job_desc>
<unzip_input><zipfilename>runtime.zip</zipfilename></unzip_input>
<task>
<application>python/bin/python3.13</application>
<command_line>-s app/science_driver.py --manifest boinc_resolve(manifest.json) --engine bin/scaling_cpu --output boinc_resolve(result.json) --checkpoint checkpoint.json --receipt receipts.json --progress fraction_done.txt --build A</command_line>
<setenv>PYTHONHOME=$PWD/python</setenv>
<append_cmdline_args/>
<multi_process/>
<checkpoint_filename>checkpoint.json</checkpoint_filename>
<fraction_done_filename>fraction_done.txt</fraction_done_filename>
<stdout_filename>science.stdout</stdout_filename>
<stderr_filename>science.stderr</stderr_filename>
</task>
</job_desc>
'''
    (base/'job.xml').write_text(job)
    (base/'controls.json').write_bytes((kit/'controls.json').read_bytes())
    (base/'engine-identity').write_bytes((kit/'bin/scaling_cpu').read_bytes())
    metadata=dict(TEST_ONLY=True,new_scientific_coverage=False,architecture='arm64',boinc_platform='arm64-apple-darwin',
        build='A',backend='cpu',source_commit=build['source_commit'],cpu_kit_sha256=PINNED_KIT_SHA256,
        wrapper_url=WRAPPER_URL,wrapper_sha256=WRAPPER_SHA256,python_url=PYTHON_URL,python_sha256=PYTHON_SHA256,
        engine_sha256=sha((kit/'bin/scaling_cpu').read_bytes()),runtime_unpacked_bytes=sum(i.file_size for i in zipfile.ZipFile(payload).infolist()),
        files={name:sha((base/name).read_bytes()) for name in ('wrapper','runtime.zip','job.xml','controls.json','engine-identity')})
    (base/'BOINC_BUILD.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kit-tar',required=True);p.add_argument('--destination',required=True);a=p.parse_args()
    print(json.dumps(package(a.kit_tar,a.destination),indent=2))
