"""Direct science integration tests, NOT a substitute for BOINC acceptance."""
import copy,hashlib,json,os,signal,subprocess,sys,tempfile,time,unittest
from pathlib import Path
APP=Path(__file__).resolve().parents[1]/'app';sys.path.insert(0,str(APP))
RUNTIME=Path(os.environ['FIFTH42_RUNTIME']).resolve();sys.path.insert(0,str(RUNTIME))
from validate_result import validate
from science_driver import atomic,digest
class Science(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name)
  rows=[json.loads(l) for l in (RUNTIME/'data/packets.jsonl').read_text().splitlines()]
  self.rows=[r for r in rows if r['group']=='control']
  self.m=dict(schema='fifth42-boinc-test-v1',TEST_ONLY=True,new_scientific_coverage=False,packets=self.rows)
  atomic(self.d/'manifest.json',self.m);self.engine=RUNTIME/'bin/scaling_cpu';self.hash=digest(self.engine.read_bytes())
  self.env=dict(os.environ,PYTHONPATH=str(RUNTIME)+os.pathsep+str(APP))
 def tearDown(self):self.tmp.cleanup()
 def command(self,*extra):return [sys.executable,str(APP/'science_driver.py'),'--engine',str(self.engine),'--build','A',*extra]
 def run_app(self,*extra):return subprocess.run(self.command(*extra),cwd=self.d,env=self.env,capture_output=True,text=True,timeout=30)
 def validate(self):return validate(self.d/'manifest.json',self.d/'result.json',RUNTIME/'bin/gmp_reference',self.hash,'A')
 def test_controls_and_corruptions(self):
  run=self.run_app();self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(self.validate()['packets'],3)
  original=json.loads((self.d/'result.json').read_text())
  mutations=[lambda r:r.update(manifest_sha256='0'*64),lambda r:r.update(completed_prefix=True),lambda r:r['receipts'].pop(),lambda r:r['receipts'][0]['response'].update(points_visited=2),lambda r:r['receipts'][0]['response']['counts'][0].update(visited=True),lambda r:r['receipts'][0]['response'].update(hits=[]),lambda r:r.update(engine_sha256='0'*64),lambda r:r.update(build='B')]
  for mutation in mutations:
   r=copy.deepcopy(original);mutation(r);atomic(self.d/'result.json',r)
   with self.assertRaises((ValueError,KeyError,TypeError)):self.validate()
  (self.d/'result.json').write_text('{')
  with self.assertRaises(ValueError):self.validate()
 def test_zero_exit_corruption_controls(self):
  for kind in ['identity','count','truncated']:
   with self.subTest(kind=kind):
    run=self.run_app('--corrupt-output',kind);self.assertEqual(run.returncode,0,run.stderr)
    with self.assertRaises(ValueError):self.validate()
 def test_actual_process_interruption(self):
  log=(self.d/'interrupted.log').open('w');p=subprocess.Popen(self.command('--pause-after','1'),cwd=self.d,env=self.env,stdout=log,stderr=log)
  try:
   end=time.monotonic()+15
   while not (self.d/'checkpoint.json').exists() and time.monotonic()<end:time.sleep(.02)
   self.assertTrue((self.d/'checkpoint.json').exists());p.kill();p.wait(timeout=5)
  finally:
   if p.poll() is None:p.kill();p.wait()
   log.close()
  self.assertFalse((self.d/'result.json').exists());run=self.run_app();self.assertEqual(run.returncode,0,run.stderr);self.validate()
  r=json.loads((self.d/'result.json').read_text());self.assertEqual(r['resumed_prefix'],1);self.assertEqual(len(r['attempts']),2);self.assertEqual(len(r['receipts']),3)
 def test_uncommitted_receipt_suffix_recomputed(self):
  run=self.run_app('--fail-after','1');self.assertNotEqual(run.returncode,0)
  p=self.d/'receipts.json';r=json.loads(p.read_text());r['receipts'].append({'uncommitted':'not credited'});atomic(p,r)
  run=self.run_app();self.assertEqual(run.returncode,0,run.stderr);self.validate();r=json.loads((self.d/'result.json').read_text());self.assertEqual(r['resumed_prefix'],1)
 def test_checkpoint_wrong_identity_rejected(self):
  self.run_app('--fail-after','1');p=self.d/'checkpoint.json';r=json.loads(p.read_text());r['manifest_sha256']='wrong';atomic(p,r)
  self.assertNotEqual(self.run_app().returncode,0)
 def test_checkpoint_corrupt_receipt_rejected(self):
  self.run_app('--fail-after','1');p=self.d/'receipts.json';r=json.loads(p.read_text());r['receipts'][0]['response']['points_visited']=999;atomic(p,r)
  self.assertNotEqual(self.run_app().returncode,0)
if __name__=='__main__':unittest.main(verbosity=2)
