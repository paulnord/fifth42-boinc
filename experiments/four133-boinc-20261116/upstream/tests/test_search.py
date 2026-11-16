#!/usr/bin/env python3
"""Cartesian oracle does not use complement buckets or C++ range helpers."""
from collections import Counter
from itertools import combinations_with_replacement
import hashlib,json,os,random,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from math133 import Case,Q,D,POWERS,REQUIRED,cases,max_gap,counts,total_counts
from audit import validate,fields,digest

def oracle(B,old,case,m):
    S=case.S;sign=case.sign;out=[];rows=[];p=[pow(x,133,m) for x in range(B+1)]
    for h in range(1,case.H+1):
        # Independently write the pair inequalities, inclusive of repeated bases.
        if case.pattern=='22':
            left=[(c+h+S,-c,c) for c in range(1,B+1) if c+h+S<=B-h]
            right=[(b,-b-h,b) for b in range(1,B+1) if b+h<=B and b+h>old and b>=S+h+1]
        else:
            left=[(S+h-b,b,b) for b in range(1,B+1) if 1<=S+h-b<=b<=B-h]
            right=[(c,-c-h,c) for c in range(1,B+1) if c+h<=B and c+h>old and 2*c>=S+h]
        allowed={tuple(sorted((v[i],v[j]))) for v in [REQUIRED[sign]] for i in range(4) for j in range(i+1,4)}
        left=[x for x in left if tuple(sorted(pow(y,133,Q) for y in x[:2])) in allowed]
        right=[x for x in right if tuple(sorted(pow(y,133,Q) for y in x[:2])) in allowed]
        raw=canonical=distinct=0
        for x in left:
            for y in right:
                v=x[:2]+y[:2]
                if sorted(pow(z,133,Q) for z in v)!=list(REQUIRED[sign]):continue
                if sum(pow(z,133,m) for z in v)%m!=(42*sign)%m:continue
                raw+=1
                if case.pattern=='22':
                    a,negc=x[:2];b,negd=y[:2]
                    if a>b:continue
                    v=(a,b,negc,negd);isdistinct=a<b
                else:
                    a,b=x[:2];c,negd=y[:2]
                    if b>c:continue
                    v=(a,b,c,negd);isdistinct=a<b<c
                canonical+=1;distinct+=isdistinct
                out.append((h,tuple(sign*z for z in v),isdistinct))
        rows.append((len(left),len(right),raw,canonical,distinct))
    return sorted(out),rows

def run():
    start=time.monotonic();sha=digest(ROOT/'src/search.cpp');records=[];positive=0;repeats=0;boundaries=0
    image=sorted(set(POWERS));assert len(image)==13
    for sign in (1,-1):
        assert [v for v in combinations_with_replacement(image,4) if sum(v)%Q==(42*sign)%Q]==[REQUIRED[sign]]
    assert D==2*3*5*7*13*23*67
    for x in range(-3000,3001):assert (x**133-x)%D==0
    assert cases(44)==[]
    for B in (200,400,1000,4000000,8000000,20000000):
        wanted=[42+k*D for k in range(-20,21) if -2*B<=42+k*D<=2*B+42]
        assert sorted({c.sign*c.S for c in cases(B)})==wanted
    env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0')
    with tempfile.TemporaryDirectory() as temp:
        for B,S in ((400,42),(400,100),(400,300),(400,600),(1000,42),(1000,600),(1000,1500)):
            for pattern in ('22','31'):
                for sign in (1,-1):
                    case=Case(pattern,S,sign,max_gap(B,S,sign,pattern))
                    if not case.H:continue
                    for old in (0,B//2,B-1):
                        expected,rows=oracle(B,old,case,43)
                        positive+=len(expected);repeats+=sum(not x[2] for x in expected);boundaries+=sum(max(map(abs,x[1]))==B for x in expected)
                        for binary in ('search','search-sanitized'):
                            intervals=[(1,case.H)]
                            if case.H>1 and binary=='search':intervals += [(1,case.H//2),(case.H//2+1,case.H)]
                            combined=[]
                            for lo,hi in intervals:
                                path=Path(temp)/'log'
                                cmd=[str(ROOT/binary),pattern,str(B),str(old),'43',str(S),str(sign),str(lo),str(hi),sha,'synthetic','1000000']
                                with path.open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.PIPE,env=env,check=True)
                                report=validate(path,B,old,case,43,lo,hi,sha,True)
                                got=sorted((x['h'],tuple(x['bases']),x['distinct']) for x in report['candidates'])
                                assert got==[x for x in expected if lo<=x[0]<=hi]
                                actual=[tuple(int(r[k]) for k in ('left','right','raw','canonical','distinct')) for r in report['checkpoints']]
                                assert actual==rows[lo-1:hi]
                                if (lo,hi)!=(1,case.H):combined+=got
                            if combined:assert sorted(combined)==expected
                        records.append(dict(B=B,old=old,S=S,sign=sign,pattern=pattern,H=case.H,candidates=len(expected)))
        # Invalid production residue, modulus, gap, and range configurations fail closed.
        base=[str(ROOT/'search'),'22','5000000','4000000',str(2305843009213693951),'42','1','1','1',sha,'production','10000']
        for i,value in ((1,'other'),(2,'20000001'),(3,'5000000'),(4,'43'),(5,'43'),(6,'0'),(7,'0'),(8,'999999')):
            cmd=base.copy();cmd[i]=value
            assert subprocess.run(cmd,capture_output=True).returncode!=0
    assert positive>0 and repeats>0 and boundaries>0,(positive,repeats,boundaries)
    # Fast period sums versus a direct per-gap sum across parity and min/max switches.
    planner=0
    for B,old,S in ((200000,50000,42000),(200000,99500,198000),(300000,70000,42000),(100000,0,42)):
        for pattern in ('22','31'):
            for sign in (1,-1):
                c=Case(pattern,S,sign,max_gap(B,S,sign,pattern))
                if not c.H:continue
                direct=tuple(sum(counts(B,old,c,h)[i] for h in range(1,c.H+1)) for i in (0,1))
                assert total_counts(B,old,c)==direct,(B,old,c,direct,total_counts(B,old,c))
                planner+=1
    report=dict(passed=True,configurations=len(records),positive_modular_controls=positive,repeated_base_controls=repeats,boundary_controls=boundaries,planner_cases=planner,exact_target42_solutions_found=0,source_sha256=sha,binary_sha256=digest(ROOT/'search'),sanitized_binary_sha256=digest(ROOT/'search-sanitized'),seconds=time.monotonic()-start,cases=records)
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))

if __name__=='__main__':run()
