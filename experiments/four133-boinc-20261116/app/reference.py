"""Independent bounded modular pair joins; no native buckets or range helpers."""
from collections import Counter, defaultdict

Q = 1597
IMAGE = tuple(pow(r,133,Q) for r in range(Q))
REQUIRED = {1:(1,1,325,1312), -1:(285,1272,1596,1596)}


def reference(task):
    B, old, S, sign, modulus = (task[k] for k in ('bound','previous_bound','normalized_sum','sign','modulus'))
    pair22 = task['pattern'] == '22'
    wanted = REQUIRED[sign]
    allowed = {tuple(sorted((wanted[i],wanted[j]))) for i in range(4) for j in range(i+1,4)}
    rows = []
    candidates = []
    for h in range(task['start'],task['end']+1):
        # These inequalities are independent of math133.ranges/counts.
        if pair22:
            lo, hi = 1, B-2*h-S
            rl, rh = max(S+h+1, old-h+1), B-h
            left_pair = lambda x: (x+h+S, -x)
        else:
            lo, hi = (S+h+1)//2, min(B-h,S+h-1)
            rl, rh = max((S+h+1)//2,old-h+1), B-h
            left_pair = lambda x: (S+h-x,x)
        right_pair = lambda x: (x,-x-h)

        def pairs(low, high, transform):
            for residue in range(Q):
                a,b = transform(residue)
                if tuple(sorted((IMAGE[a%Q],IMAGE[b%Q]))) not in allowed:
                    continue
                for x in range(low+(residue-low)%Q,high+1,Q):
                    a,b = transform(x)
                    yield (a,b), (pow(a,133,modulus)+pow(b,133,modulus))%modulus

        left = defaultdict(list)
        nleft = nright = raw = canonical = distinct = 0
        for pair, value in pairs(lo,hi,left_pair):
            left[value].append(pair)
            nleft += 1
        for right, value in pairs(rl,rh,right_pair):
            nright += 1
            for first in left.get((42*sign-value)%modulus, ()):
                normalized = first+right
                if tuple(sorted(IMAGE[x%Q] for x in normalized)) != wanted:
                    continue
                raw += 1
                if pair22:
                    a,negc = first
                    b,negd = right
                    if a>b:
                        continue
                    normalized = a,b,negc,negd
                    isdistinct = a<b
                else:
                    a,b = first
                    c,negd = right
                    if b>c:
                        continue
                    isdistinct = a<b<c
                canonical += 1
                distinct += isdistinct
                candidates.append((h,tuple(sign*x for x in normalized),isdistinct))
        rows.append(dict(h=h,left=nleft,right=nright,raw=raw,canonical=canonical,distinct=distinct))
    return rows, sorted(candidates)
