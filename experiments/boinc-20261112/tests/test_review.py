"""Independent adversarial review; direct tests, not BOINC lifecycle evidence."""
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import test_science
from science_driver import atomic

class IndependentReview(unittest.TestCase):
 setUp=test_science.Science.setUp
 tearDown=test_science.Science.tearDown
 command=test_science.Science.command
 run_app=test_science.Science.run_app
 validate=test_science.Science.validate
 def test_additional_malformed_outputs(self):
  run=self.run_app();self.assertEqual(run.returncode,0,run.stderr)
  original=json.loads((self.d/'result.json').read_text())
  mutations={
   'float_total':lambda r:r['receipts'][0]['response'].update(points_visited=3.0),
   'string_count':lambda r:r['receipts'][0]['response']['counts'][0].update(visited='3'),
   'duplicate_receipt':lambda r:r['receipts'].__setitem__(1,copy.deepcopy(r['receipts'][0])),
   'reordered_receipts':lambda r:r['receipts'].reverse(),
   'wrong_packet':lambda r:r['receipts'][0].update(packet_sha256='0'*64),
   'scope_promoted':lambda r:r.update(new_scientific_coverage=True),
   'missing_hits':lambda r:r['receipts'][0]['response'].pop('hits'),
   'bool_hit_coordinate':lambda r:r['receipts'][0]['response']['hits'][0].update(a=True),
  }
  for label,mutation in mutations.items():
   with self.subTest(label=label):
    result=copy.deepcopy(original);mutation(result);atomic(self.d/'result.json',result)
    with self.assertRaises((ValueError,KeyError,TypeError)):self.validate()
 def test_receipt_without_checkpoint_recomputes(self):
  run=self.run_app('--fail-after','1');self.assertNotEqual(run.returncode,0)
  (self.d/'checkpoint.json').unlink()
  run=self.run_app();self.assertEqual(run.returncode,0,run.stderr);self.validate()
  result=json.loads((self.d/'result.json').read_text());self.assertEqual(result['resumed_prefix'],0)
 def test_checkpoint_overshoots_durable_receipts(self):
  self.run_app('--fail-after','1');path=self.d/'checkpoint.json';c=json.loads(path.read_text());c['completed_prefix']=3;atomic(path,c)
  self.assertNotEqual(self.run_app().returncode,0)
if __name__=='__main__':unittest.main(verbosity=2)
