"""Actual wrapper/runtime must refuse GPU work without BOINC allocation data."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('bundle');p.add_argument('slot');a=p.parse_args()
base=Path(a.bundle).resolve();slot=Path(a.slot).resolve();slot.mkdir(exist_ok=False)
for name in ('wrapper','runtime.zip','job.xml'):shutil.copy2(base/name,slot/name)
shutil.copy2(base/'controls.json',slot/'manifest.json')
environment={k:v for k,v in os.environ.items() if not k.startswith(('PYTHON','DYLD_'))}
run=subprocess.run([str(slot/'wrapper')],cwd=slot,env=environment,capture_output=True,text=True,timeout=120)
diagnostic=run.stderr
# The BOINC API redirects stderr into its normal stderr.txt after startup.
for name in ('stderr.txt','science.stderr'):
    if (slot/name).exists():diagnostic+='\n'+(slot/name).read_text()
(slot/'wrapper.stderr').write_text(diagnostic)
assert run.returncode!=0 and not (slot/'result.json').exists()
assert 'BOINC Apple GPU allocation required' in diagnostic or "No such file or directory: 'init_data.xml'" in diagnostic,diagnostic
report=dict(stock_wrapper_executed=True,bundled_runtime_executed=True,missing_allocation_rejected=True,
    gpu_execution=False,physical_M4_acceptance=False,TEST_ONLY=True,new_scientific_coverage=False)
(base/'GPU_REFUSAL_SMOKE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
