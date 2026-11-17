"""A missing CUDA device must fail, never silently execute a CPU substitute."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from make_work import make
from protocol import atomic
from search import gpu

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('engine');p.add_argument('output');a=p.parse_args()
    engine=str(Path(a.engine).resolve())
    with tempfile.TemporaryDirectory() as tmp:
        # An invalid allocation is deliberately invisible to CUDA even on a GPU runner.
        task=make('no-device',[21],2,10)['tasks'][0]
        try:gpu(task,'999',engine,Path(tmp)/'test')
        except ValueError as error:
            if 'CUDA execution failed' not in str(error):raise
            expected=('no CUDA-capable device','CUDA driver version is insufficient','initialization error',
                      'invalid device ordinal','unsupported display driver')
            if not any(message in str(error) for message in expected):raise
            report=dict(native_windows_executable_started=True,missing_device_rejected=True,
                        positive_GPU_arithmetic_acceptance=False,reason=str(error))
        else:raise RuntimeError('An unallocated GPU unexpectedly executed')
    atomic(a.output,report)
    print(json.dumps(report,indent=2))
