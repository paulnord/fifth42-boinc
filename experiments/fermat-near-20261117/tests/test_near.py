import copy
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from protocol import atomic, canonical, load_manifest, validate_manifest, sha
from make_work import make
from search import cpu, gpu, metal
from validate import oracle, validate, InfrastructureUnavailable
from driver import allocation


class Science(unittest.TestCase):
    def test_all_exponents_against_full_triple_oracle_and_gmp(self):
        for n in range(4, 33):
            for k in (Fraction(1), Fraction(n), Fraction(7, 3)):
                task = make('control', [n], 2, 35, k=k)['tasks'][0]
                expected = [[a, b, c, str(a**n + b**n - c**n)]
                    for c in range(2, 36) for a in range(1, c) for b in range(a, c)
                    if 0 < abs(a**n + b**n - c**n) * k.denominator <= k.numerator * c**(n-3)]
                self.assertEqual(cpu(task)['hits'], expected)
                self.assertEqual(oracle(task, os.environ['NEAR_GMP']), cpu(task))

    def test_known_fifth_boundary_and_repeated_bases(self):
        task = make('boundary', [5], 17, 17, k=Fraction(12, 289))['tasks'][0]
        self.assertIn([13, 16, 17, '12'], cpu(task)['hits'])
        task['k_num'] = 11
        self.assertNotIn([13, 16, 17, '12'], cpu(task)['hits'])
        repeated = make('equal', [8], 12, 12)['tasks'][0]
        self.assertTrue(any(a == b == 11 for a, b, c, d in cpu(repeated)['hits']))

    def test_manifest_overlap_strict_types_and_budgets(self):
        valid = make('valid', [21, 32], 2, 20)
        for mutate in [lambda m: m['tasks'][0].update(exponent=True),
                       lambda m: m['tasks'][0].update(last_c=20001),
                       lambda m: m['tasks'][0].update(k_den=0),
                       lambda m: m['tasks'].append(dict(m['tasks'][0], id=2))]:
            value = copy.deepcopy(valid); mutate(value)
            with self.assertRaises(ValueError): validate_manifest(value)

    def test_allocation_requires_assigned_gpu(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'init.xml'
            p.write_text('<app_init_data><ncpus>1</ncpus></app_init_data>')
            self.assertEqual(allocation(p, 'cpu', None), 'BOINC')
            with self.assertRaises(ValueError): allocation(p, 'gpu', '0')
            p.write_text('<app_init_data><ncpus>1</ncpus><gpu_type>NVIDIA</gpu_type><gpu_device_num>0</gpu_device_num></app_init_data>')
            self.assertEqual(allocation(p, 'gpu', '0'), 'BOINC')
            with self.assertRaises(ValueError): allocation(p, 'gpu', '$GPU_DEVICE_NUM')
            p.write_text('<app_init_data><ncpus>1</ncpus><gpu_type>apple_gpu</gpu_type><gpu_device_num>0</gpu_device_num></app_init_data>')
            self.assertEqual(allocation(p, 'metal', '0'), 'BOINC')
            with self.assertRaises(ValueError): allocation(p, 'gpu', '0')

    def test_forged_omitted_candidates_and_retryable_oracle(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            manifest = make('forged', [21, 32], 2, 30)
            atomic(p / 'work.json', manifest)
            result = dict(schema='fermat-near-result-v1', purpose='TEST_ONLY', new_scientific_coverage=False,
                manifest_sha256=sha((p/'work.json').read_bytes()), build_identity='test', backend='cpu',
                delivery='BOINC', gpu_device=None, boinc_ncpus=1, completed_tasks=2, resumed_tasks=0,
                records=[dict(task=t, science=cpu(t)) for t in manifest['tasks']], elapsed_seconds=0)
            atomic(p/'result.json', result)
            self.assertTrue(validate(p/'work.json', p/'result.json', os.environ['NEAR_GMP'], 'test', 'cpu')['scientifically_accepted'])
            with self.assertRaises(InfrastructureUnavailable):
                validate(p/'work.json', p/'result.json', '/missing/oracle', 'test', 'cpu')
            result['records'][0]['science']['hits'] = []
            atomic(p/'result.json', result)
            with self.assertRaises(ValueError):
                validate(p/'work.json', p/'result.json', os.environ['NEAR_GMP'], 'test', 'cpu')

    def test_durable_restart_and_changed_prefix_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            shutil.copytree(ROOT/'app', p/'app', ignore=shutil.ignore_patterns('__pycache__'))
            build = dict(backend='cpu', files={})
            atomic(p/'NEAR_BUILD.json', build)
            manifest = make('restart', [21, 32], 2, 30, pause=60)
            atomic(p/'manifest.json', manifest)
            command = [sys.executable, 'app/driver.py', '--backend', 'cpu', '--standalone']
            with (p/'first.log').open('w') as log:
                child = subprocess.Popen(command, cwd=p, stdout=log, stderr=log)
                try:
                    deadline = time.monotonic() + 10
                    while not (p/'checkpoint.json').exists():
                        self.assertIsNone(child.poll())
                        self.assertLess(time.monotonic(), deadline)
                        time.sleep(.02)
                finally:
                    child.terminate(); child.wait(timeout=10)
            prefix = (p/'chunk-000.json').read_bytes()
            (p/'chunk-000.json').write_bytes(prefix + b' ')
            # JSON whitespace does not change the committed canonical science.
            result = subprocess.run(command, cwd=p, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((p/'result.json').read_text())['resumed_tasks'], 1)
            chunk = json.loads((p/'chunk-000.json').read_text()); chunk['science']['hits'] = []
            atomic(p/'chunk-000.json', chunk)
            result = subprocess.run(command, cwd=p, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)


@unittest.skipUnless(os.environ.get('NEAR_GPU'), 'CUDA engine/device not selected')
class Cuda(unittest.TestCase):
    def test_all_requested_exponents_and_wide_arithmetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n in range(21, 33):
                for first, last in [(2, 40), (998, 1000), (19999, 20000)]:
                    task = make('cuda', [n], first, last)['tasks'][0]
                    self.assertEqual(gpu(task, '0', os.environ['NEAR_GPU'], Path(tmp)/'task'), cpu(task))

    def test_threshold_equality_repeated_variables_and_overflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n, c, k in [(5, 17, Fraction(12,289)), (5,17,Fraction(11,289)), (8,12,Fraction(8))]:
                task = make('cuda', [n], c, c, k=k)['tasks'][0]
                self.assertEqual(gpu(task, '0', os.environ['NEAR_GPU'], Path(tmp)/'task'), cpu(task))
            task = make('overflow', [21], 2, 40, k=Fraction(1000000))['tasks'][0]
            with self.assertRaises(ValueError):
                gpu(task, '0', os.environ['NEAR_GPU'], Path(tmp)/'task', capacity=1)


@unittest.skipUnless(os.environ.get('NEAR_METAL'), 'Physical M4 Metal engine/device not selected')
class Metal(unittest.TestCase):
    def test_all_exponents_and_wide_arithmetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n in range(4,33):
                for first,last in [(2,40),(998,1000)]:
                    task=make('metal',[n],first,last)['tasks'][0]
                    self.assertEqual(metal(task,'0',os.environ['NEAR_METAL'],Path(tmp)/'task'),cpu(task))

    def test_rational_boundary_and_output_overflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            for k in (Fraction(12,289),Fraction(11,289)):
                task=make('metal',[5],17,17,k=k)['tasks'][0]
                self.assertEqual(metal(task,'0',os.environ['NEAR_METAL'],Path(tmp)/'task'),cpu(task))
            task=make('overflow',[21],2,40,k=Fraction(1000000))['tasks'][0]
            with self.assertRaises(ValueError):
                metal(task,'0',os.environ['NEAR_METAL'],Path(tmp)/'task',capacity=1)


if __name__ == '__main__':
    unittest.main()
