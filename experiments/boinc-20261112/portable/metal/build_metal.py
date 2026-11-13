"""Build native macOS Metal pilot; distinguish compilation from real GPU tests."""
import argparse,hashlib,json,os,platform,shutil,subprocess,sys,tarfile
from pathlib import Path
from generate_shader import generate
from test_arithmetic import test

HERE=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('workspace');p.add_argument('--test-first-device',action='store_true',help='CI only: authorize testing the first enumerated GPU');p.add_argument('--device-registry-id');a=p.parse_args()
if sys.platform!='darwin':p.error('Requires a native macOS build host')
base=Path(a.workspace).resolve()
def run(command,**kwargs):return subprocess.run(list(map(str,command)),check=True,**kwargs)
# Reuse the already validated pinned bundle acquisition, CPU/GMP and parent/I/O
# adaptation. Its full CPU checks remain a prerequisite for this new GPU pilot.
run([sys.executable,HERE/'portable/build_native.py',base,'--compiler','clang++'])
runtime=base/'runtime';generated=base/'metal-generated';shader=generate(runtime,generated)
host_math=test(runtime,base/'metal-host-math','clang++')
run(['xcrun','-sdk','macosx','metal','-std=macos-metal2.4','-c',generated/'fifth42.metal','-o',generated/'fifth42.air'])
run(['xcrun','-sdk','macosx','metallib',generated/'fifth42.air','-o',generated/'fifth42.metallib'])
source=Path(__file__).parent/'scaling_metal.mm';engine=runtime/'bin/scaling_gpu'
run(['clang++','-std=c++17','-O3','-fobjc-arc','-pthread','-I',runtime/'native/src','-I',generated,source,
    '-framework','Foundation','-framework','Metal','-o',engine])
probe=run([engine,'--list-devices'],capture_output=True,text=True)
devices=json.loads(probe.stdout)['devices'];(base/'METAL_DEVICES.json').write_text(json.dumps(devices,indent=2)+'\n')
kit=base/'metal-kit';shutil.copytree(base/'client-kit',kit)
(kit/'bin/scaling_cpu').unlink();shutil.copy2(engine,kit/'bin/scaling_gpu')
(kit/'test_client.py').unlink();shutil.copy2(Path(__file__).parent/'test_metal_client.py',kit/'test_metal_client.py')
shutil.copy2(Path(__file__).parent/'METAL_TESTING.md',kit/'README.md')
# A CPU success must never masquerade as GPU test evidence in this kit.
(kit/'NATIVE_TEST_EVIDENCE.json').unlink();(kit/'BUILD.json').unlink()
selected=a.device_registry_id
if a.test_first_device and devices:selected=devices[0]['registry_id']
report=dict(TEST_ONLY=True,new_scientific_coverage=False,host_compiled=True,
    gpu_execution=False,shader_offline_compiled=True,devices=devices,host_arithmetic=host_math,shader=shader,
    prototype_commit=subprocess.check_output(['git','-C',HERE,'rev-parse','HEAD'],text=True).strip(),
    platform=platform.platform(),architecture=platform.machine())
if selected:
    assert any(x['registry_id']==selected for x in devices),'Selected Metal device unavailable'
    from test_gpu import run_tests
    report['gpu_tests']=run_tests(base,selected)
    environment=dict(os.environ,FIFTH42_METAL_REGISTRY_ID=selected)
    run([sys.executable,runtime/'colab_bench.py','--backend','gpu','--repeats','1','--max-seconds','600','--verify-gmp'],env=environment)
    shutil.copy2(runtime/'results/benchmark-gpu.json',kit/'METAL_GMP_EVIDENCE.json')
    run([sys.executable,kit/'test_metal_client.py','--device-registry-id',selected,'--destination',base/'metal-kit-smoke'])
    report.update(status='gpu_tests_passed',gpu_execution=True,selected_registry_id=selected)
else:report.update(status='host_compiled_gpu_not_tested',reason='No authorized Metal device selected or available')
files={str(f.relative_to(kit)):hashlib.sha256(f.read_bytes()).hexdigest() for f in kit.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
report['files']=files;(kit/'METAL_BUILD.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open(base/'metal-kit.tar.gz','w:gz') as archive:
    archive.add(kit,arcname='metal-kit',filter=lambda item:None if '__pycache__' in Path(item.name).parts else item)
print(json.dumps(report,indent=2))
