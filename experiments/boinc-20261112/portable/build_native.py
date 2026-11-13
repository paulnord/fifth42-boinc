#!/usr/bin/env python3
"""Build/test native CPU application kits; no BOINC server or production access."""
import argparse,hashlib,json,os,platform,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('workspace');p.add_argument('--compiler',default='g++');a=p.parse_args()
base=Path(a.workspace).resolve();base.mkdir(exist_ok=False)
inputs=base/'inputs';runtime=base/'runtime';kit=base/'client-kit'
def run(cmd,**kwargs):subprocess.run(list(map(str,cmd)),check=True,**kwargs)
run(['git','clone','--filter=blob:none','--no-checkout','https://github.com/paulnord/fifth42.git',inputs])
run(['git','-C',inputs,'-c','core.autocrlf=false','checkout','--detach','4668a27951f2b9d7d533896d1aa32684808341d4'])
run([sys.executable,inputs/'colab/20261112/load_bundle.py','--destination',runtime])
header=runtime/'native/src/stream_io.hpp';original_bytes=header.read_bytes();original=original_bytes.decode()
include='#include <sys/prctl.h>\n#include <unistd.h>'
start=original.index('inline void protect_parent()');end=original.index('\ninline bool read_frame',start)
assert original.count(include)==1
portable=original[:start]+original[end:]
portable=portable.replace(include,'#include "parent_guard.hpp"')
header.write_text(portable,newline='\n');shutil.copy2(HERE/'portable/parent_guard.hpp',header.parent/'parent_guard.hpp')
oracle_source=runtime/'native/independent/gmp_reference.cpp'
original_oracle=oracle_source.read_bytes()
benchmark=runtime/'colab_bench.py';original_benchmark=benchmark.read_bytes()
text=original_benchmark.decode();start=text.index('def hardware():');end=text.index('\ndef main(',start)
text=text[:start]+(HERE/'portable/hardware.py').read_text()+'\n'+text[end:]
benchmark.write_text(text,newline='\n')
if os.name=='nt':
    shutil.copy2(HERE/'portable/windows_engine_session.py',runtime/'engine_session.py')
    # Windows LLP64 makes C++ long 32-bit. Keep the independent oracle's exact
    # coordinate domain and construct GMP bases from decimal int64 strings.
    text=original_oracle.decode()
    replacements={
        'unsigned id;long low,high;std::array<long,3> j;std::array<std::array<long,3>,3> u;':
        'unsigned id;std::int64_t low,high;std::array<std::int64_t,3> j;std::array<std::array<std::int64_t,3>,3> u;',
        'for(long n2=':'for(std::int64_t n2=', 'for(long n1=':'for(std::int64_t n1=', 'for(long n0=':'for(std::int64_t n0=',
        'const long c=v[0],a=v[1],b=v[2];mpz_class ap,bp,cp;':
        'const std::int64_t c=v[0],a=v[1],b=v[2];mpz_class ap,bp,cp; const mpz_class az(std::to_string(a)),bz(std::to_string(b)),cz(std::to_string(c));',
        'mpz_ui_pow_ui(ap.get_mpz_t(),a,5);mpz_ui_pow_ui(bp.get_mpz_t(),b,5);mpz_ui_pow_ui(cp.get_mpz_t(),c,5);':
        'mpz_pow_ui(ap.get_mpz_t(),az.get_mpz_t(),5);mpz_pow_ui(bp.get_mpz_t(),bz.get_mpz_t(),5);mpz_pow_ui(cp.get_mpz_t(),cz.get_mpz_t(),5);',
        'mpz_class(5)*c*c':'mpz_class(5)*cz*cz',
        'volume*=2*bound+1;':'if(volume>10000000/(2*bound+1))throw std::runtime_error("work limit");volume*=2*bound+1;'
    }
    for old,new in replacements.items():
        assert text.count(old)==1,old
        text=text.replace(old,new)
    oracle_source.write_text(text,newline='\n')
(runtime/'bin').mkdir();suffix='.exe' if os.name=='nt' else ''
common=['-std=c++17','-O3','-pthread']
if os.name=='nt':common+=['-static']
gmp_flags=[]
if sys.platform=='darwin':
    prefix=subprocess.check_output(['brew','--prefix','gmp'],text=True).strip()
    gmp_flags=['-I'+prefix+'/include','-L'+prefix+'/lib']
run([a.compiler,*common,runtime/'native/src/scaling_cpu.cpp','-o',runtime/'bin'/('scaling_cpu'+suffix)])
run([a.compiler,*common,*gmp_flags,runtime/'native/independent/gmp_reference.cpp','-lgmpxx','-lgmp','-o',runtime/'bin'/('gmp_reference'+suffix)])
if os.name=='nt':
    # Keep the Linux prototype test paths usable while CreateProcess resolves
    # their .exe sibling. Both files contain the identical PE executable.
    for name in ('scaling_cpu','gmp_reference'):shutil.copy2(runtime/'bin'/(name+suffix),runtime/'bin'/name)
env=dict(os.environ,FIFTH42_RUNTIME=str(runtime))
for pattern in ('test_science.py','test_review.py','test_gpu_allocation.py'):
    run([sys.executable,'-m','unittest','discover','-s',HERE/'tests','-p',pattern,'-v'],env=env)
run([sys.executable,runtime/'colab_bench.py','--backend','cpu','--repeats','1','--max-seconds','180','--verify-gmp'])
(kit/'bin').mkdir(parents=True);(kit/'app').mkdir()
shutil.copy2(runtime/'bin'/('scaling_cpu'+suffix),kit/'bin'/('scaling_cpu'+suffix))
shutil.copy2(runtime/'engine_session.py',kit/'app/engine_session.py');shutil.copy2(runtime/'colab_bench.py',kit/'app/colab_bench.py')
driver=(HERE/'app/science_driver.py').read_text().replace('APPLICATION_BUILD="prototype-dev"','APPLICATION_BUILD="A"')
(kit/'app/science_driver.py').write_text(driver)
run([sys.executable,HERE/'scripts/make_manifest.py','--catalog',runtime/'data/packets.jsonl','--output',kit/'controls.json','--names','control-cap100-r12','control-cap42-r12','control-cap2951-r-2002'])
shutil.copy2(HERE/'portable/test_client.py',kit/'test_client.py')
shutil.copy2(HERE/'portable/CLIENT_KITS.md',kit/'README.md')
shutil.copy2(runtime/'results/benchmark-cpu.json',kit/'NATIVE_TEST_EVIDENCE.json')
files={str(f.relative_to(kit)):hashlib.sha256(f.read_bytes()).hexdigest() for f in kit.rglob('*') if f.is_file()}
metadata=dict(TEST_ONLY=True,new_scientific_coverage=False,platform=platform.platform(),architecture=platform.machine(),python=sys.version,
    compiler=subprocess.check_output([a.compiler,'--version'],text=True),source_commit='4668a27951f2b9d7d533896d1aa32684808341d4',
    original_stream_io_sha256=hashlib.sha256(original_bytes).hexdigest(),adapted_stream_io_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),files=files)
metadata.update(original_oracle_sha256=hashlib.sha256(original_oracle).hexdigest(),adapted_oracle_sha256=hashlib.sha256(oracle_source.read_bytes()).hexdigest())
metadata.update(original_benchmark_sha256=hashlib.sha256(original_benchmark).hexdigest(),adapted_benchmark_sha256=hashlib.sha256(benchmark.read_bytes()).hexdigest())
(kit/'BUILD.json').write_text(json.dumps(metadata,indent=2)+'\n')
run([sys.executable,kit/'test_client.py','--destination',base/'kit-smoke'])
with tarfile.open(base/'client-kit.tar.gz','w:gz') as archive:
    archive.add(kit,arcname='client-kit',filter=lambda item:None if '__pycache__' in Path(item.name).parts else item)
print(json.dumps(dict(status='passed',kit=str(kit),platform=metadata['platform'])))
