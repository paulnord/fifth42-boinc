"""Generate immutable bounded gap work; search mode preserves upstream guards."""
import argparse
import json
from protocol import MODULI, SOURCE_SHA, validate_manifest

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--bound',required=True,type=int)
    p.add_argument('--previous-bound',default=4000000,type=int)
    p.add_argument('--pattern',choices=['22','31'],default='22')
    p.add_argument('--normalized-sum',default=42,type=int)
    p.add_argument('--sign',choices=[-1,1],default=1,type=int)
    p.add_argument('--first-gap',required=True,type=int)
    p.add_argument('--gap-count',default=1,type=int)
    p.add_argument('--unit-id',required=True)
    p.add_argument('--search',action='store_true',help='Search guards; coverage credit requires separate campaign admission')
    p.add_argument('--output',required=True)
    a=p.parse_args()
    tasks=[dict(id=i,pattern=a.pattern,bound=a.bound,previous_bound=a.previous_bound,
        normalized_sum=a.normalized_sum,sign=a.sign,start=a.first_gap,end=a.first_gap+a.gap_count-1,
        modulus=m,engine_mode='production') for i,m in enumerate(MODULI)]
    value=dict(schema='four133-work-v1',exponent=133,target=42,purpose='SEARCH' if a.search else 'TEST_ONLY',
        unit_id=a.unit_id,source_sha256=SOURCE_SHA,tasks=tasks,test_pause_after=0,test_pause_seconds=0)
    entries=validate_manifest(value)
    with open(a.output,'x') as out:json.dump(value,out,indent=2);out.write('\n')
    print(json.dumps(dict(output=a.output,expected_pair_entries=entries,new_scientific_coverage=False)))
