"""Test the allocated-device boundary without assuming physical GPU zero."""
import argparse,contextlib,io,os,sys,unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
sys.path.insert(0,os.environ['FIFTH42_RUNTIME'])
import test_science
import science_driver

class GPUAllocation(unittest.TestCase):
    setUp=test_science.Science.setUp
    tearDown=test_science.Science.tearDown
    def args(self,device):
        return argparse.Namespace(backend='gpu',gpu_device=device,manifest=self.d/'manifest.json',
            engine=self.engine,build='A',checkpoint=self.d/'checkpoint.json',progress=self.d/'progress.json',max_seconds=30)
    def test_uses_assigned_device_and_preserves_other_environment(self):
        original=dict(CUDA_VISIBLE_DEVICES='7',OTHER='retained')
        with mock.patch.dict(os.environ,original),mock.patch('science_driver.EngineSession',side_effect=RuntimeError('PROBE')) as engine:
            with contextlib.redirect_stdout(io.StringIO()),self.assertRaisesRegex(RuntimeError,'PROBE'):
                science_driver.main(self.args('3'))
            selected=engine.call_args.kwargs['environment']
            self.assertEqual(selected['CUDA_VISIBLE_DEVICES'],'3')
            self.assertEqual(selected['OTHER'],'retained')
            self.assertEqual(os.environ['CUDA_VISIBLE_DEVICES'],'7')
    def test_missing_or_ambiguous_allocation_fails_closed(self):
        for device in (None,'','-1','0,1','GPU-anything','１２'):
            with self.subTest(device=device),self.assertRaises(ValueError):science_driver.main(self.args(device))

if __name__=='__main__':unittest.main()
