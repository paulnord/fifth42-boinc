"""Translate pinned integer evaluator types/address spaces, retaining formulas."""
import hashlib,json,re
from pathlib import Path

def generate(runtime,destination):
    runtime=Path(runtime);destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    exact=(runtime/'native/vendor/exact.hpp').read_text()
    kernel=(runtime/'native/src/kernel.hpp').read_text()
    common=exact[exact.index('struct Upper128'):exact.index('inline I192 pack')]
    common+=kernel[kernel.index('using U64='):]
    old=common[common.index('HD inline std::uint64_t high_product'):common.index('// Exact low 192 bits.')]
    high='''HD inline std::uint64_t high_product(std::uint64_t a,std::uint64_t b) {
    // Exact high half using bounded 32-bit partial products; no native uint128.
    const std::uint64_t mask=0xffffffffULL;
    const auto a0=a&mask,a1=a>>32,b0=b&mask,b1=b>>32;
    const auto w0=a0*b0;
    const auto t=a1*b0+(w0>>32);
    const auto w1=(t&mask)+a0*b1;
    return a1*b1+(t>>32)+(w1>>32);
}
'''
    common=common.replace(old,high)
    common=common.replace('using U64=unsigned long long;','using U64=ulong;')
    common=common.replace('std::uint64_t','ulong').replace('std::int64_t','long')
    magnitude='const auto m=static_cast<ulong>(x<0?-x:x);'
    assert common.count(magnitude)==2
    common=common.replace(magnitude,'const auto raw=static_cast<ulong>(x); const auto m=x<0?ulong(0)-raw:raw;')
    common=common.replace('UINT64_C(1)','ulong(1)').replace('UINT64_MAX','0xffffffffffffffffUL')
    common=common.replace('HD ','').replace('const Task&','const F42_THREAD Task&').replace('Candidate&','F42_THREAD Candidate&')
    common=re.sub(r'(\d)ULL\b',r'\1UL',common)
    assert '__int128' not in common and 'std::' not in common and '#if' not in common
    common+='\nstatic_assert(sizeof(Task)==120,"task layout");\nstatic_assert(sizeof(Chunk)==24,"chunk layout");\nstatic_assert(sizeof(Candidate)==40,"candidate layout");\n'
    (destination/'metal_common.hpp').write_text(common)
    body=(Path(__file__).parent/'kernels.metal').read_text()
    # Metal requires an explicit constant address space for program globals.
    shader_common=re.sub(r'^constexpr ', 'constant ', common, flags=re.MULTILINE)
    shader='#include <metal_stdlib>\nusing namespace metal;\n#define F42_THREAD thread\n'+shader_common+'\n'+body
    (destination/'fifth42.metal').write_text(shader)
    assert ')F42METAL"' not in shader
    (destination/'metal_shader.hpp').write_text('static const char* fifth42_shader=R"F42METAL('+shader+')F42METAL";\n')
    metadata={name:hashlib.sha256((runtime/name).read_bytes()).hexdigest() for name in ('native/vendor/exact.hpp','native/src/kernel.hpp')}
    metadata['shader_sha256']=hashlib.sha256(shader.encode()).hexdigest()
    (destination/'SHADER_SOURCE.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('runtime');p.add_argument('destination');a=p.parse_args();generate(a.runtime,a.destination)
