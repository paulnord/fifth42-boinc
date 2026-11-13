import json,socket
from pathlib import Path
plain_bind={}
for port in (3306,8765,31420):
    with socket.socket() as s:
        try:
            s.bind(('127.0.0.1',port));plain_bind[port]='available'
        except OSError as exc:
            plain_bind[port]=str(exc)
    # TCP TIME_WAIT after a clean shutdown can obstruct a bare bind even with
    # no listeners. Real servers reuse their address; still refuse any listener.
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        s.bind(('127.0.0.1',port))
active=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdecimal():continue
    try:
        cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
    except (FileNotFoundError,PermissionError):continue
    if any(name in cmd for name in ('mariadbd','/apache2','/bin/boinc ','/bin/feeder','/bin/transitioner','/bin/script_validator','fifth42_CabbageA_wrapper','scaling_cpu','science_driver.py')):
        active.append(dict(pid=proc.name,command=cmd))
assert not active,active
record=dict(stopped_cleanly=True,ports_available_with_so_reuseaddr=[3306,8765,31420],plain_bind_after_shutdown=plain_bind,remaining_service_processes=active)
Path('/evidence/cleanup.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
