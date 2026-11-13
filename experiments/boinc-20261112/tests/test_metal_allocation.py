"""Explicit direct-pilot Metal allocation; no claim of BOINC device mapping."""
import contextlib,io,os,sys,unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).parent))
import test_gpu_allocation
import science_driver

class MetalAllocation(test_gpu_allocation.GPUAllocation):
    def args(self,device):
        a=super().args(None);a.backend='metal';a.metal_device_registry_id=device;return a
    def test_uses_assigned_device_and_preserves_other_environment(self):
        with mock.patch.dict(os.environ,dict(FIFTH42_METAL_REGISTRY_ID='7',OTHER='retained')),mock.patch('science_driver.EngineSession',side_effect=RuntimeError('PROBE')) as engine:
            with contextlib.redirect_stdout(io.StringIO()),self.assertRaisesRegex(RuntimeError,'PROBE'):
                science_driver.main(self.args('1234567'))
            self.assertEqual(engine.call_args.kwargs['environment']['FIFTH42_METAL_REGISTRY_ID'],'1234567')
            self.assertEqual(engine.call_args.kwargs['environment']['OTHER'],'retained')
            self.assertEqual(os.environ['FIFTH42_METAL_REGISTRY_ID'],'7')
    def test_missing_or_ambiguous_allocation_fails_closed(self):
        for device in (None,'','0','-1','0,1','GPU-anything','１２',str(2**64)):
            with self.subTest(device=device),self.assertRaises(ValueError):science_driver.main(self.args(device))
