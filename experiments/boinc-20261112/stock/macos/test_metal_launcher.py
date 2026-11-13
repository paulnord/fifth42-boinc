import copy,json,tempfile,unittest
from pathlib import Path
from metal_boinc_launcher import arithmetic_cases,expected,select_device,verify_arithmetic

class Allocation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'init_data.xml'
        self.write('apple_gpu','0');self.device=dict(name='Apple M4',registry_id='123456789',unified_memory=True)
    def tearDown(self):self.tmp.cleanup()
    def write(self,kind,number):self.path.write_text(f'<app_init_data><gpu_type>{kind}</gpu_type><gpu_device_num>{number}</gpu_device_num></app_init_data>')
    def test_explicit_unique_allocation(self):
        self.assertEqual(select_device(self.path,'0',[self.device]),'123456789')
        self.assertEqual(select_device(self.path,None,[self.device]),'123456789')
    def test_missing_ambiguous_or_conflicting_allocation(self):
        for number in ('','-1','0,1','$GPU_DEVICE_NUM','０','1'):
            with self.subTest(number=number),self.assertRaises(ValueError):select_device(self.path,number,[self.device])
        for devices in ([],[self.device,self.device],[dict(self.device,name='Apple Paravirtual device')],[dict(self.device,registry_id='')]):
            with self.assertRaises(ValueError):select_device(self.path,'0',devices)
        for kind,number in (('NVIDIA','0'),('','-1'),('apple_gpu','1'),('apple_gpu','-1')):
            self.write(kind,number)
            with self.assertRaises(ValueError):select_device(self.path,'0',[self.device])
        self.write('','-1')
        with self.assertRaises(ValueError):select_device(self.path,None,[self.device])
    def test_arithmetic_fault_is_rejected(self):
        rows=arithmetic_cases();values=[]
        for a,b in rows:
            x=expected(a,b);values.append(dict(p=x[:3],q=x[3:6],sum=x[6:9],negative=x[9:12],square5=x[12:15],lt=x[15],eq=x[16]))
        verify_arithmetic(rows,dict(arithmetic=values))
        bad=copy.deepcopy(values);bad[2]['q'][0]^=1
        with self.assertRaises(ValueError):verify_arithmetic(rows,dict(arithmetic=bad))
        with self.assertRaises(ValueError):verify_arithmetic(rows,dict(arithmetic=values[:-1]))

if __name__=='__main__':unittest.main()
