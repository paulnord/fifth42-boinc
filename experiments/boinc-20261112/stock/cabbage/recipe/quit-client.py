import os,subprocess,time
from pathlib import Path
s=Path(os.environ['STOCK'])
key=(s/'client/gui_rpc_auth.cfg').read_text().strip()
subprocess.run([str(s/'root/usr/bin/boinccmd'),'--host','127.0.0.1:31420','--passwd',key,'--quit'],check=True)
pid=int((s/'client.pid').read_text())
for _ in range(100):
    p=Path(f'/proc/{pid}/stat')
    if not p.exists() or p.read_text().split(') ',1)[1].startswith('Z'):
        print('BOINC client exited after GUI RPC quit',flush=True)
        break
    time.sleep(.1)
else:
    raise TimeoutError('Client did not exit cleanly')
# Do not leave a stale PID for the stack's generic cleanup.
(s/'client.pid').unlink()
