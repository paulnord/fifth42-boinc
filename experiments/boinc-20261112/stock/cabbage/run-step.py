#!/usr/bin/env python3
"""Log exact container commands and sample aggregate cgroup resource usage."""
import datetime, json, pathlib, subprocess, sys, time
base=pathlib.Path(__file__).resolve().parent
name,mode,*args=sys.argv[1:]
log=base/'evidence'/f'{name}.log'
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
command=[str(base/'container.sh'),mode,*args]
record=dict(command=command,started_utc=started,memory_peak_bytes=0,pids_peak=0)
with log.open('w') as f:
    child=subprocess.Popen(command,stdout=f,stderr=subprocess.STDOUT)
    cg=pathlib.Path(f'/sys/fs/cgroup/user.slice/user-{__import__("os").getuid()}.slice/user@{__import__("os").getuid()}.service/app.slice/fifth42-boinc-pilot-{mode}-{child.pid}.scope')
    record['cgroup']=str(cg)
    while child.poll() is None:
        try:
            record['memory_peak_bytes']=max(record['memory_peak_bytes'],int((cg/'memory.peak').read_text()))
            record['pids_peak']=max(record['pids_peak'],int((cg/'pids.current').read_text()))
            record['cpu_stat_last_sample']=(cg/'cpu.stat').read_text()
            record['memory_events_last_sample']=(cg/'memory.events').read_text()
            record['limits']={k:(cg/k).read_text().strip() for k in ('cpu.max','memory.max','memory.swap.max','pids.max')}
        except FileNotFoundError:
            pass
        time.sleep(0.25)
record.update(exit_code=child.returncode,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(base/'evidence'/f'{name}-resources.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
sys.exit(child.returncode)
