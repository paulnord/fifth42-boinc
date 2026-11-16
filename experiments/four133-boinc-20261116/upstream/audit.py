"""Strict chunk validation, independent pair counts, and exact candidate checks."""
from collections import Counter
import hashlib
from pathlib import Path
from math133 import Q,D,REQUIRED,counts

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def fields(line):
    tokens=line.split();out={}
    for token in tokens[1:]:
        k,v=token.split('=',1)
        if k in out:raise ValueError('duplicate field')
        out[k]=v
    return out

def validate(path,B,old,case,m,lo,hi,source_sha,test=False):
    lines=Path(path).read_text().splitlines()
    assert lines[0].startswith('START ') and lines[-1].startswith('CHUNK_DONE '),'incomplete chunk'
    head=fields(lines[0]);tail=fields(lines[-1])
    required=dict(version=2,pattern=case.pattern,bound=B,previous_bound=old,modulus=m,normalized_sum=case.S,sign=case.sign,normalized_target=42*case.sign,max_gap=case.H,start=lo,end=hi,test_mode=int(test),source_sha=source_sha)
    assert all(head.get(k)==str(v) for k,v in required.items()),head
    assert all(tail.get(k)==str(required[k]) for k in ('pattern','bound','previous_bound','modulus','normalized_sum','sign','start','end'))
    total=Counter();emitted=Counter();distincts=Counter();candidates=[];checkpoints=[];prev=lo-1;maxrss=0;wall=0.
    for line in lines[1:-1]:
        row=fields(line)
        if line.startswith('CANDIDATE '):
            h=int(row['h']);v=tuple(int(row[k]) for k in 'abcd')
            assert h==prev+1 and lo<=h<=hi
            assert 0 not in v and old<max(map(abs,v))<=B and sum(v)==case.sign*case.S
            assert sorted(pow(x,133,Q) for x in v)==list(REQUIRED[1])
            assert sum(pow(x,133,m) for x in v)%m==42%m
            if not test:assert sum(v)%D==42
            a,b,c,d=(case.sign*x for x in v)
            if case.pattern=='22':
                c=-c;d=-d
                assert 0<c<a<=b<d and d-b==h and a-c==case.S+h
                distinct=a<b
            else:
                d=-d
                assert 0<a<=b<=c<d and d-c==h and a+b==case.S+h
                distinct=a<b<c
            assert int(row['distinct'])==distinct
            residual=sum(x**133 for x in v)-42
            candidates.append(dict(h=h,bases=list(v),residual=str(residual),exact=residual==0,distinct=distinct))
            emitted[h]+=1;distincts[h]+=distinct
        elif line.startswith('CHECKPOINT '):
            h=int(row['h']);assert h==prev+1 and h<=hi
            expected=counts(B,old,case,h)
            assert (int(row['left']),int(row['right']))==expected,(h,row,expected)
            assert int(row['canonical'])==emitted[h] and int(row['distinct'])==distincts[h]
            assert 0<=int(row['distinct'])<=int(row['canonical'])<=int(row['raw'])
            for k in ('left','right','raw','canonical','distinct'):total[k]+=int(row[k])
            wall=float(row['wall']);assert wall>=0
            maxrss=max(maxrss,int(row['rss_kib']));prev=h;checkpoints.append(row)
        else:raise ValueError('unknown log record')
    assert prev==hi
    assert all(int(tail[k])==total[k] for k in ('left','right','raw','canonical','distinct'))
    return dict(sha256=digest(path),totals=dict(total),candidates=candidates,exact=[x for x in candidates if x['exact']],peak_rss_kib=maxrss,setup_seconds=float(head['setup_seconds']),wall_seconds=wall,checkpoints=checkpoints)
