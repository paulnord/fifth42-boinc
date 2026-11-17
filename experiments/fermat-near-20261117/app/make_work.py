"""Generate bounded c-row chunks, with rational K or the paper's r cutoff."""
import argparse
from fractions import Fraction
from protocol import atomic, validate_manifest


def make(name, exponents, first, last, k=None, min_score=Fraction(1), rows=128, pause=0):
    tasks = []
    for n in exponents:
        coefficient = Fraction(k) if k is not None else Fraction(n) / Fraction(min_score)
        for low in range(first, last + 1, rows):
            tasks.append(dict(id=len(tasks), exponent=n, first_c=low,
                last_c=min(last, low + rows - 1), k_num=coefficient.numerator, k_den=coefficient.denominator))
    value = dict(schema='fermat-near-work-v1', purpose='TEST_ONLY', unit_id=name, tasks=tasks,
                 pause_after=1 if pause else 0, pause_seconds=pause)
    return validate_manifest(value)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--exponents', required=True, help='Comma-separated integer exponents, e.g. 21,22,23')
    p.add_argument('--first-c', type=int, default=2)
    p.add_argument('--last-c', type=int, default=1000)
    p.add_argument('--chunk-rows', type=int, default=128)
    p.add_argument('--unit-id', required=True)
    group = p.add_mutually_exclusive_group()
    group.add_argument('--k', type=Fraction)
    group.add_argument('--min-score', type=Fraction, default=Fraction(1))
    p.add_argument('--pause-seconds', type=int, default=0)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    value = make(a.unit_id, [int(n) for n in a.exponents.split(',')], a.first_c, a.last_c,
                 a.k, a.min_score, a.chunk_rows, a.pause_seconds)
    from pathlib import Path
    if Path(a.output).exists():
        p.error('Output already exists')
    atomic(a.output, value)
