# General finite-box reduction for four 133rd powers

The equation is a^133+b^133+c^133+d^133=42, with signed integer bases.
All ranges below include equality where stated; repeated bases are retained
until after the raw modular join. No old search result is altered by this proof.

## Residues and normalized ordinary sums

Let D=4,206,930=2*3*5*7*13*23*67. Each prime p has p-1 dividing 132;
therefore x^133=x mod D for every integer x. The ordinary sum s satisfies
s=42 mod D. As in the archived proof, -2B<=s<=2B+42: two terms of each
sign give |s|<2B; with three positive terms, a smallest positive base would
exceed the negative magnitude by >42 if s>2B+42; the reflected argument
excludes s<-2B. All-positive or all-negative tuples cannot sum to 42.

Enumerate EVERY s=42+kD in that interval. None is zero. If s>0, put S=s,
T=42; if s<0, negate all four bases and put S=-s,T=-42. Thus S>=42 and
T<=S in all normalized cases. Negation is undone before exact candidate
checking. No fixed list of ordinary sums is used.

Enumeration of the 13 133rd-power residues modulo 1597 gives the
unique four-element multiset (1,1,325,1312) summing to 42, including repetitions.
For normalized T=-42 it is (285,1272,1596,1596). Zero is absent, so no base
is zero or divisible by 1597. These finite enumerations are independently tested.

For positive normalized S, one positive and three negative terms are impossible:
the positive base exceeds their sum by S>=42, and strict superadditivity makes
the power sum greater than 42. Consequently only the following patterns remain.

## Two positive, two negative

Write the tuple (a,b,-c,-d), a<=b and c<=d. If b>=d, the positive pair weakly
majorizes the negative pair and has strictly larger sum. For the strictly
increasing convex g(x)=x^133-x on positive integers, this implies
g(a)+g(b)>g(c)+g(d). Hence T>S, contradicting T<=S. An elementary proof
compares componentwise when a>=c; otherwise the interval [d,b] is longer
than [a,c] by S and lies to its right, so its integral of g' is larger.

Therefore b<d. Put h=d-b>=1. The ordinary-sum relation gives a=c+h+S,
and the canonical order is 0<c<a<=b<d<=B. Since a<=b<=B-h,
2h<=B-S-1. The full inclusive generation ranges can be pruned to

* left c: 1<=c<=B-2h-S, with a=c+h+S;
* right b: max(S+h+1,old-h+1)<=b<=B-h, with d=b+h.

For f(x)=x^133, the left increment is at most 133(h+S)a^132, while the right
increment is at least 133h*a^132+133*66*h^2*a^131. Thus
T<=133*a^131*(S*a-66h^2). For T=42, positivity requires 66h^2<S*a<=S*B.
For T=-42, if 66h^2>=S*a+1, the upper bound is <=-133*a^131<-42,
also impossible. Thus 66h^2<=S*a<=S*B. Use the strict or nonstrict integer
square-root bound, intersected with floor((B-S-1)/2). This introduces the
previously omitted two-positive branches whenever a nonzero ordinary-sum
multiple becomes smaller than B.

Join a^133-c^133 with d^133-b^133+T modulo each sieve modulus. Retain raw
equal-residue multiplicities, then enforce a<=b; a=b is deliberately included.

## Three positive, one negative

Write (a,b,c,-d), 1<=a<=b<=c. Necessarily d>c. If d<c then the integer jump
c^133-d^133 is already >42. If d=c, a^133+b^133 is either 2 or >=2^133+1,
never +/-42. Put d=c+h, h>=1. Then a+b=S+h and the full inclusive ranges are

* left b: ceil((S+h)/2)<=b<=min(B-h,S+h-1), with a=S+h-b;
* right c: max(ceil((S+h)/2),old-h+1)<=c<=B-h.

The ordinary-sum geometry gives 3h<=2B-S. Also
133h*c^132<=2c^133-T. For T=42, 135h<2B; for T=-42, integrality and
42/c^132<1 give 135h<=2B. Here c>=2; c=1 would yield 3-d^133, never +/-42.

A second bound uses b<=S+h-1. The same argument with b instead of c gives
133h<2b for T=42, or 133h<=2b for T=-42 (b>=2 in every possible solution;
b=1 gives a=b=1 and cannot have power sum -42). Thus
131h<2S-2 or 131h<=2S-2 respectively. Intersect all three bounds. For
S=T=42 this yields no h, recovering the earlier exclusion of this pattern.

Join a^133+b^133 with d^133-c^133+T. Retain a=b and b=c in raw/canonical
matching; distinctness is a separate flag.

## Shell, completeness, and arithmetic

In every branch d is the unique largest absolute base. Applying d>old only
to the right list therefore enumerates exactly old<max|base|<=B, including
new h values and all needed old left pairs. Its union with the verified old
box establishes a larger box only after ALL cases and gaps finish and are
independently reconciled. Partial completion is never a full-box result.

Pair buckets retain precisely the possible splits of the forced modulo-1597
multiset, with every equal-residue Cartesian product retained. Any true exact
solution survives both necessary moduli. Every emitted candidate is checked
with Python arbitrary-precision integers after undoing normalization.

Modular powers use unsigned 128-bit multiplication for operands below 2^63;
their product is below 2^126. The two production moduli are below 2^61, so
pair addition is below 2^62. Bounds are capped at 20,000,000; all range, gap
and square comparisons fit unsigned 64 bits. Sources and executables are
fingerprinted; new code never resumes archived checkpoints.

This is a mathematical reduction plus tested computational evidence, not a
formal executable certificate. The old archive and its raw production logs
must be verified before claiming the prior-box union.
