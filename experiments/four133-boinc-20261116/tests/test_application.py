import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from driver import allocation, inspect_log
from protocol import canonical,make_controls,sha,validate_manifest
from reference import reference
from validate import InfrastructureUnavailable,validate


@unittest.skipUnless(os.environ.get('FOUR133_TEST_BUILD'),'Native build required')
class NativeApplication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build=Path(os.environ['FOUR133_TEST_BUILD']).resolve()
        cls.meta=json.loads((cls.build/'BOINC_BUILD.json').read_text())

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.slot=Path(self.temp.name)
        self.manifest=make_controls()

    def tearDown(self):
        self.temp.cleanup()

    def command(self):
        return [sys.executable,str(ROOT/'app/driver.py'),'--standalone',
            '--engine',str(self.build/'payload/bin/four133_engine'),
            '--build',str(self.build/'payload/FOUR133_BUILD.json')]

    def execute(self):
        (self.slot/'manifest.json').write_text(json.dumps(self.manifest))
        run=subprocess.run(self.command(),cwd=self.slot,capture_output=True,text=True,timeout=30)
        if run.returncode:
            logs='\n'.join(p.read_text() for p in self.slot.glob('*.partial'))
            self.fail(run.stderr+'\n'+logs)
        return json.loads((self.slot/'result.json').read_text())

    def check(self):
        return validate(self.slot/'manifest.json',self.slot/'result.json',
                        self.build/'gmp_exact',self.meta['engine_sha256'],'standalone')

    def test_real_native_controls_and_exact_oracle(self):
        result=self.execute();audit=self.check()
        self.assertEqual(result['completed_tasks'],4)
        self.assertGreater(audit['GMP_candidate_checks'],0)
        self.assertEqual(audit['exact_hits'],[])
        self.assertFalse(audit['new_scientific_coverage'])

    def test_checkpoint_stop_and_resume(self):
        self.manifest.update(test_pause_after=1,test_pause_seconds=60)
        (self.slot/'manifest.json').write_text(json.dumps(self.manifest))
        child=subprocess.Popen(self.command(),cwd=self.slot,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            end=time.monotonic()+15
            while not (self.slot/'checkpoint.json').exists() and child.poll() is None and time.monotonic()<end:
                time.sleep(.05)
            self.assertTrue((self.slot/'checkpoint.json').exists())
            child.terminate();child.communicate(timeout=10)
            self.assertEqual(json.loads((self.slot/'checkpoint.json').read_text())['completed_tasks'],1)
            subprocess.run(self.command(),cwd=self.slot,capture_output=True,text=True,check=True,timeout=30)
            self.assertEqual(json.loads((self.slot/'result.json').read_text())['resumed_tasks'],1)
            self.assertTrue(self.check()['scientifically_accepted'])
        finally:
            if child.poll() is None:child.kill();child.communicate()

    def test_changed_committed_log_refuses_resume(self):
        self.execute()
        (self.slot/'task-000.log').write_text('changed')
        result=subprocess.run(self.command(),cwd=self.slot,capture_output=True,text=True,timeout=15)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Committed native log changed',result.stderr)

    def test_reject_identity_truncation_counts_and_strict_types(self):
        original=self.execute()
        variants=[]
        bad=copy.deepcopy(original);bad['manifest_sha256']='0'*64;variants.append(bad)
        bad=copy.deepcopy(original);bad['records'].pop();variants.append(bad)
        bad=copy.deepcopy(original);bad['completed_tasks']=True;variants.append(bad)
        bad=copy.deepcopy(original);bad['boinc_ncpus']=True;variants.append(bad)
        bad=copy.deepcopy(original);bad['records'][0]['task_id']=1;variants.append(bad)
        bad=copy.deepcopy(original);bad['records'][0]['log']=bad['records'][0]['log'].replace('left=','left=9',1)
        bad['records'][0]['log_sha256']=sha(bad['records'][0]['log'].encode());variants.append(bad)
        for index,bad in enumerate(variants):
            with self.subTest(variant=index):
                (self.slot/'result.json').write_text(json.dumps(bad))
                with self.assertRaises((ValueError,AssertionError)):self.check()

    def test_omitted_candidates_even_with_self_consistent_worker_counts(self):
        result=self.execute()
        index=next(i for i,t in enumerate(self.manifest['tasks']) if reference(t)[1])
        log=result['records'][index]['log']
        lines=[]
        import re
        for line in log.splitlines():
            if line.startswith('CANDIDATE '):continue
            line=re.sub(r'canonical=\d+','canonical=0',line)
            line=re.sub(r'distinct=\d+','distinct=0',line)
            lines.append(line)
        forged='\n'.join(lines)+'\n'
        path=self.slot/'forged.log';path.write_text(forged)
        inspect_log(path,self.manifest['tasks'][index])
        result['records'][index].update(log=forged,log_sha256=sha(forged.encode()))
        (self.slot/'result.json').write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError,'Independent'):self.check()

    def test_oracle_failure_is_infrastructure(self):
        self.execute()
        with self.assertRaises(InfrastructureUnavailable):
            validate(self.slot/'manifest.json',self.slot/'result.json',self.slot/'missing-oracle',self.meta['engine_sha256'])


class AllocationAndScope(unittest.TestCase):
    def test_reference_matches_preserved_cartesian_oracle(self):
        import importlib.util
        from protocol import task_case
        from math133 import max_gap
        spec=importlib.util.spec_from_file_location('upstream_oracle',ROOT/'upstream/tests/test_search.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        checked=0
        for B,S in ((400,42),(400,300),(1000,600)):
            for pattern in ('22','31'):
                for sign in (1,-1):
                    H=max_gap(B,S,sign,pattern)
                    if not H:continue
                    for old in (0,B//2,B-1):
                        task=dict(pattern=pattern,bound=B,previous_bound=old,normalized_sum=S,sign=sign,
                                  start=1,end=min(4,H),modulus=43)
                        candidates,rows=module.oracle(B,old,task_case(task),43)
                        actual,wanted=reference(task)
                        self.assertEqual(wanted,[x for x in candidates if x[0]<=task['end']])
                        self.assertEqual([tuple(r[k] for k in ('left','right','raw','canonical','distinct')) for r in actual],rows[:task['end']])
                        checked+=1
        self.assertGreaterEqual(checked,20)

    def test_boinc_requires_one_cpu_and_no_gpu(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'init_data.xml'
            for cpus,gpu in [('2',''),('nan',''),('1','apple_gpu')]:
                path.write_text(f'<app_init_data><ncpus>{cpus}</ncpus><gpu_type>{gpu}</gpu_type></app_init_data>')
                with self.assertRaises(ValueError):allocation(path)
            path.write_text('<app_init_data><ncpus>1</ncpus></app_init_data>')
            self.assertEqual(allocation(path),'BOINC')

    def test_synthetic_controls_cannot_be_credited_as_search(self):
        manifest=make_controls();manifest['purpose']='SEARCH'
        with self.assertRaises(ValueError):validate_manifest(manifest)

    def test_duplicate_oversize_or_wrong_equation_work_is_refused(self):
        for key,value in [('exponent',5),('target',41),('exponent',True)]:
            manifest=make_controls();manifest[key]=value
            with self.assertRaises(ValueError):validate_manifest(manifest)
        manifest=make_controls();manifest['tasks'][0]['end']=99999
        with self.assertRaises(ValueError):validate_manifest(manifest)


if __name__=='__main__':unittest.main()
