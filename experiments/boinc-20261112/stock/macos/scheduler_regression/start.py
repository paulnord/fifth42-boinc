import argparse,os,shutil,subprocess
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--lab',required=True);a=parser.parse_args()
b=Path(a.lab).resolve();recipe=Path(__file__).resolve().parent
stock=b/'work/mac-plan-regression';stock.mkdir(mode=0o700)
for name in ('root','source','localbin'):(stock/name).symlink_to('../stock-verify/'+name)
shutil.copy2(b/'work/mac-server/env.sh',stock/'env.sh')
(stock/'php.ini').write_text((b/'work/mac-server/php.ini').read_text().replace('/pilot/mac-server','/pilot/mac-plan-regression'))
(b/'evidence/mac-plan-regression').mkdir(mode=0o700,exist_ok=True)
cmd=['systemd-run','--user','--unit=fifth42-boinc-mac-plan-regression-20261113','--collect','--wait','--service-type=exec',
 '-p','CPUQuota=200%','-p','MemoryMax=4G','-p','MemorySwapMax=0','-p','TasksMax=256','-p','Nice=19','-p','IOSchedulingClass=idle','-p','RuntimeMaxSec=10min','-p','TimeoutStopSec=45s',
 'bwrap','--unshare-all','--uid',str(os.getuid()),'--gid',str(os.getgid()),'--hostname','fifth42-mac-plan-regression','--new-session','--die-with-parent',
 '--ro-bind',str(b/'rootfs'),'/', '--ro-bind',str(b/'mac-cpu-source'),'/source','--ro-bind',str(recipe),'/recipe','--tmpfs','/pilot',
 '--bind',str(b/'work/mac-plan-regression'),'/pilot/mac-plan-regression',
 '--ro-bind',str(b/'work/stock-verify/root'),'/pilot/stock-verify/root','--ro-bind',str(b/'work/stock-verify/source'),'/pilot/stock-verify/source','--ro-bind',str(b/'work/stock-verify/localbin'),'/pilot/stock-verify/localbin',
 '--ro-bind',str(b/'work/science/runtime'),'/pilot/science/runtime','--ro-bind',str(b/'work/mac-server/project/apps'),'/pilot/input-project/apps','--ro-bind',str(b/'work/mac-server/project/plan_class_spec.xml'),'/pilot/input-project/plan_class_spec.xml',
 '--ro-bind',str(b/'work/mac-server/metal-bundle-141'),'/pilot/bundle','--bind',str(b/'evidence/mac-plan-regression'),'/evidence',
 '--proc','/proc','--dev','/dev','--tmpfs','/tmp','--tmpfs','/run','--clearenv','--setenv','PATH','/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
 '--setenv','USER','pnord','--setenv','LOGNAME','pnord','--setenv','HOME','/pilot/mac-plan-regression','--setenv','LANG','C.UTF-8','--setenv','TZ','UTC','--chdir','/pilot/mac-plan-regression','bash','/recipe/run.sh']
with (b/'evidence/mac-plan-regression/start-command.json').open('w') as f:
 import json
 json.dump(cmd,f,indent=2)
subprocess.run(cmd,check=True)
