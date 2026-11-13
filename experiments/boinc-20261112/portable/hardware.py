def hardware():
    # Informational metadata only. Unavailable affinity/RAM remain explicit;
    # this function does not change the benchmark's work or acceptance checks.
    out=dict(python=platform.python_version(),platform=platform.platform(),
        logical_cpus=os.cpu_count(),available_cpu_affinity=None,system_ram_gib=None,
        gpu='not queried for portable CPU build',nvcc='not queried for portable CPU build')
    if hasattr(os,'sched_getaffinity'):out['available_cpu_affinity']=len(os.sched_getaffinity(0))
    try:
        if Path('/proc/meminfo').exists():
            mem=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
            out['system_ram_gib']=int(mem['MemTotal'].split()[0])/1024**2
        elif platform.system()=='Darwin':
            out['system_ram_gib']=int(subprocess.check_output(['sysctl','-n','hw.memsize'],text=True))/1024**3
        elif os.name=='nt':
            import ctypes
            from ctypes import wintypes
            class Memory(ctypes.Structure):
                _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD)]+[(name,ctypes.c_ulonglong) for name in ('physical','available','pagefile','available_pagefile','virtual','available_virtual','extended')]
            memory=Memory();memory.length=ctypes.sizeof(memory)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
                out['system_ram_gib']=memory.physical/1024**3
    except (OSError,ValueError) as exc:out['metadata_error']=type(exc).__name__
    return out
