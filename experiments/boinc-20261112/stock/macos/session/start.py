import argparse,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--lab',required=True);a=p.parse_args()
base=Path(a.lab).resolve()
recipe=Path(__file__).resolve().parent
(base/'work/mac-transport').mkdir(mode=0o700,exist_ok=True)
cmd=['systemd-run','--user','--unit=fifth42-boinc-mac-server-20261113','--collect','--service-type=exec',
 '-p','CPUQuota=200%','-p','MemoryMax=4G','-p','MemorySwapMax=0','-p','TasksMax=256','-p','Nice=19',
 '-p','IOSchedulingClass=idle','-p','RuntimeMaxSec=4h','-p','TimeoutStopSec=45s',
 'bwrap','--unshare-all','--uid',str(os.getuid()),'--gid',str(os.getgid()),'--hostname','fifth42-boinc-mac-pilot',
 '--new-session','--die-with-parent','--ro-bind',str(base/'rootfs'),'/',
 '--ro-bind',str(base/'mac-cpu-source'),'/source','--ro-bind',str(recipe),'/recipe',
 '--tmpfs','/pilot','--bind',str(base/'work/mac-server'),'/pilot/mac-server',
 '--bind',str(base/'work/mac-transport'),'/pilot/transport',
 '--ro-bind',str(base/'work/stock-verify/root'),'/pilot/stock-verify/root',
 '--ro-bind',str(base/'work/stock-verify/source'),'/pilot/stock-verify/source',
 '--ro-bind',str(base/'work/stock-verify/localbin'),'/pilot/stock-verify/localbin',
 '--ro-bind',str(base/'work/science/runtime'),'/pilot/science/runtime',
 '--bind',str(base/'evidence'),'/evidence','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--tmpfs','/run',
 '--clearenv','--setenv','PATH','/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
 '--setenv','USER','pnord','--setenv','LOGNAME','pnord','--setenv','HOME','/pilot/mac-server',
 '--setenv','LANG','C.UTF-8','--setenv','TZ','UTC','--chdir','/pilot/mac-server','bash','/recipe/mac-server.sh']
subprocess.run(cmd,check=True)
