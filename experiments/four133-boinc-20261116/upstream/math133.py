"""Independent integer range and residue-progression accounting; no C++ imports."""
from dataclasses import dataclass, asdict
from functools import lru_cache
from math import isqrt

D=4206930
Q=1597
MODULI=(2305843009213693921,2305843009213693951)
POWERS=tuple(pow(x,133,Q) for x in range(Q))
REQUIRED={1:(1,1,325,1312),-1:(285,1272,1596,1596)}
ALLOWED={sign:{tuple(sorted((v[i],v[j]))) for i in range(4) for j in range(i+1,4)} for sign,v in REQUIRED.items()}

@dataclass(frozen=True)
class Case:
    pattern:str
    S:int
    sign:int
    H:int
    @property
    def name(self):return f'{self.pattern}_s{self.sign*self.S}'

def max_gap(B,S,sign,pattern):
    if pattern=='22':return max(0,min(isqrt((S*B-(sign>0))//66),(B-S-1)//2))
    if pattern!='31':raise ValueError(pattern)
    return max(0,min((2*B-(sign>0))//135,(2*S-2-(sign>0))//131,(2*B-S)//3))

def cases(B):
    out=[]
    for k in range((-2*B-42+D-1)//D,(2*B)//D+1):
        s=42+k*D;S=abs(s);sign=1 if s>0 else -1
        for pattern in ('22','31'):
            H=max_gap(B,S,sign,pattern)
            if H:out.append(Case(pattern,S,sign,H))
    return out

def ranges(B,old,case,h):
    S=case.S
    if case.pattern=='22':return (1,B-2*h-S,max(S+h+1,old-h+1),B-h)
    return ((S+h+1)//2,min(B-h,S+h-1),max((S+h+1)//2,old-h+1),B-h)

@lru_cache(None)
def residues(kind,sign,shift):
    if kind=='L22':pair=lambda r:(POWERS[(r+shift)%Q],POWERS[-r%Q])
    elif kind=='L31':pair=lambda r:(POWERS[(shift-r)%Q],POWERS[r])
    elif kind=='R':pair=lambda r:(POWERS[r],POWERS[(-r-shift)%Q])
    else:raise ValueError(kind)
    return tuple(r for r in range(Q) if tuple(sorted(pair(r))) in ALLOWED[sign])

def count(lo,hi,rs):return sum((hi-r)//Q-(lo-1-r)//Q for r in rs) if lo<=hi else 0

def counts(B,old,case,h):
    lo,hi,rl,rh=ranges(B,old,case,h)
    return (count(lo,hi,residues('L'+case.pattern,case.sign,(h+case.S)%Q)),count(rl,rh,residues('R',case.sign,h%Q)))

def total_counts(B,old,case,start=1,end=None):
    """Exact periodic arithmetic sums, splitting every max/min crossover."""
    end=case.H if end is None else end
    points={start,end+1}
    if case.pattern=='22':cross=[(old-case.S+1)//2]
    else:cross=[(B-case.S+2)//2,(2*old-case.S+3)//3]
    points.update(x for x in cross if start<x<=end)
    points=sorted(points);answer=[0,0];period=2*Q
    for low,stop in zip(points,points[1:]):
        for h in range(low,min(stop,low+period)):
            n=(stop-1-h)//period+1
            first=counts(B,old,case,h)
            if n>1:
                second=counts(B,old,case,h+period)
                last=counts(B,old,case,h+(n-1)*period)
                assert all(last[i]==first[i]+(n-1)*(second[i]-first[i]) for i in (0,1))
            for i in (0,1):answer[i]+=n*first[i]+(n*(n-1)//2*(second[i]-first[i]) if n>1 else 0)
    return tuple(answer)
