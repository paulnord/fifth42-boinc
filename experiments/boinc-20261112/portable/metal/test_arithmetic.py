"""Check the exact generated shader arithmetic in C++; not GPU acceptance."""
import argparse,json,random,subprocess
from pathlib import Path
from generate_shader import generate

def cases():
    edge=[0,1,-1,2,-2,2**32-1,2**32,2**32+1,200000000000,-200000000000]
    rows=[(a,b) for a in edge for b in edge];rng=random.Random(424242)
    rows += [(rng.randint(-200000000000,200000000000),rng.randint(-200000000000,200000000000)) for _ in range(1000)]
    return rows

def expected(a,b):
    p=a**5;q=b**5
    def limbs(n):return [(n>>shift)&(2**64-1) for shift in (0,64,128)]
    return [*limbs(p),*limbs(q),*limbs(p+q),*limbs(-p-q),*limbs(5*a*a),int(p<q),int(p==q)]

def test(runtime,destination,compiler='g++'):
    destination=Path(destination);destination.mkdir(exist_ok=False)
    generate(runtime,destination)
    code='''#include <cstdint>
#include <iostream>
using ulong=std::uint64_t;
#define F42_THREAD
#include "metal_common.hpp"
int main(int argc,char**) {
 if(argc>1){ulong a,b;while(std::cin>>a>>b)std::cout<<high_product(a,b)<<'\\n';return 0;}
 S64 a,b;while(std::cin>>a>>b){auto r=arithmetic({a,b});
 for(auto v:{r.p,r.q,r.sum,r.negative,r.square5})std::cout<<v.lo<<' '<<v.hi.lo<<' '<<v.hi.hi<<' ';
 std::cout<<r.lt<<' '<<r.eq<<'\\n';}
}
'''
    source=destination/'arithmetic.cpp';source.write_text(code);binary=destination/'arithmetic'
    subprocess.run([compiler,'-std=c++17','-O2',str(source),'-o',str(binary)],check=True)
    rows=cases();result=subprocess.run([str(binary)],input=''.join(f'{a} {b}\n' for a,b in rows),capture_output=True,text=True,check=True,timeout=30)
    actual=[list(map(int,line.split())) for line in result.stdout.splitlines()]
    assert actual==[expected(a,b) for a,b in rows]
    rng=random.Random(42);products=[(a,b) for a in (0,1,2**32-1,2**32,2**64-1) for b in (0,1,2**32-1,2**32,2**64-1)]
    products += [(rng.getrandbits(64),rng.getrandbits(64)) for _ in range(100000)]
    result=subprocess.run([str(binary),'--products'],input=''.join(f'{a} {b}\n' for a,b in products),capture_output=True,text=True,check=True,timeout=30)
    assert list(map(int,result.stdout.split()))==[(a*b)>>64 for a,b in products]
    report=dict(status='passed',arithmetic_cases=len(rows),high_product_cases=len(products),gpu_execution=False)
    (destination/'HOST_ARITHMETIC.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('runtime');p.add_argument('destination');p.add_argument('--compiler',default='g++');a=p.parse_args();print(json.dumps(test(a.runtime,a.destination,a.compiler)))
