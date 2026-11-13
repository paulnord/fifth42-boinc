from pathlib import Path
import argparse,subprocess,shutil,sys,xml.etree.ElementTree as E
p=argparse.ArgumentParser();p.add_argument('--stock',required=True);p.add_argument('--runtime',required=True);p.add_argument('--label',required=True);p.add_argument('--build',choices=['A','B'],required=True);p.add_argument('--version',required=True);p.add_argument('--backend',choices=['cpu','gpu'],default='cpu');a=p.parse_args()
root=Path(a.stock).resolve();runtime=Path(a.runtime).resolve();repo=Path(__file__).resolve().parents[1]
label,build,version=a.label,a.build,a.version
import re
if not re.fullmatch(r'[A-Za-z0-9_-]+',label) or not re.fullmatch(r'[0-9]+\.[0-9]{2}',version):raise ValueError('Invalid immutable label/version')
bundle=root/('acceptance-bundle-'+label)
subprocess.run(['/usr/bin/python3',str(repo/'scripts/package_application.py'),'--runtime',str(runtime),'--destination',str(bundle),'--build',build,'--backend',a.backend],check=True)
platform='x86_64-pc-linux-gnu'+('__fifth42_cuda' if a.backend=='gpu' else '')
d=root/'project/apps/fifth42'/version/platform;d.mkdir(parents=True,exist_ok=False)
v=E.Element('version');E.SubElement(v,'is_wrapper');E.SubElement(v,'api_version').text='8.3.0'
files={p.name:p for p in bundle.iterdir() if p.name!='BUILD.json'}
files['wrapper']=root/'source/samples/wrapper/wrapper__x86_64-pc-linux-gnu'
job=root/('acceptance-job-'+label+'.xml')
engine='scaling_gpu' if a.backend=='gpu' else 'scaling_cpu'
gpu_args=' --backend gpu --gpu-device $GPU_DEVICE_NUM' if a.backend=='gpu' else ''
job.write_text('<job_desc>\n<task>\n<application>/usr/bin/python3</application>\n<command_line>science_driver.py --manifest boinc_resolve(manifest.json) --engine boinc_resolve('+engine+') --output boinc_resolve(result.json) --checkpoint checkpoint.json --receipt receipts.json --progress fraction_done.txt --build '+build+gpu_args+'</command_line>\n<append_cmdline_args/>\n<multi_process/>\n<checkpoint_filename>checkpoint.json</checkpoint_filename>\n<fraction_done_filename>fraction_done.txt</fraction_done_filename>\n<stdout_filename>science.stdout</stdout_filename>\n<stderr_filename>science.stderr</stderr_filename>\n</task>\n</job_desc>\n')
files['job.xml']=job
for logical,src in files.items():
 physical='fifth42_'+label+'_'+logical;shutil.copy2(src,d/physical)
 if logical in ['wrapper','scaling_cpu','scaling_gpu']:(d/physical).chmod(0o755)
 f=E.SubElement(v,'file');E.SubElement(f,'physical_name').text=physical;E.SubElement(f,'logical_name').text=logical;E.SubElement(f,'copy_file')
 if logical=='wrapper':E.SubElement(f,'main_program')
E.ElementTree(v).write(d/'version.xml',encoding='unicode')
