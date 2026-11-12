"""Unit-level DB boundary probes only; does not simulate BOINC acceptance."""
import sys,unittest,os
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
sys.path.insert(0,os.environ['FIFTH42_RUNTIME'])
from boinc_validate import resolve
class Mapping(unittest.TestCase):
 def setUp(self):
  self.config=dict(mysql_command=['mysql'],database='prototype',workunits={'wu_a':{'manifest':'trusted_a.json','allowed_app_version_ids':[7]}},application_versions={'7':{'build':'A'},'8':{'build':'B'}})
 def test_mapping_uses_server_not_upload(self):
  with patch('boinc_validate.subprocess.check_output',return_value='wu_a\t7\n') as execute:
   name,version,work,app=resolve(self.config,'12')
   self.assertEqual(work['manifest'],'trusted_a.json');self.assertEqual(app['build'],'A');self.assertIn('r.id=12',execute.call_args.args[0][-1])
 def test_injection_rejected(self):
  with self.assertRaises(ValueError):resolve(self.config,'1;DROP TABLE result')
 def test_wrong_version_rejected(self):
  with patch('boinc_validate.subprocess.check_output',return_value='wu_a\t8\n'):
   with self.assertRaises(ValueError):resolve(self.config,'12')
 def test_unknown_workunit_rejected(self):
  with patch('boinc_validate.subprocess.check_output',return_value='wu_other\t7\n'):
   with self.assertRaises(KeyError):resolve(self.config,'12')
if __name__=='__main__':unittest.main()
