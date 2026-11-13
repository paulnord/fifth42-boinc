"""Kill a real parent while keeping its engine input pipe open externally."""
import ctypes,json,os,queue,signal,subprocess,sys,threading,time,unittest
from pathlib import Path

class ParentLifetime(unittest.TestCase):
    def test_engine_exits_when_parent_dies_even_with_open_input(self):
        root=Path(os.environ['FIFTH42_RUNTIME'])
        engine=root/'bin'/('scaling_cpu.exe' if os.name=='nt' else 'scaling_cpu')
        program='''import json,subprocess,sys,time
p=subprocess.Popen([sys.argv[1]],stdin=sys.stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
print(json.dumps(dict(engine_pid=p.pid)),flush=True)
print(json.dumps(dict(ready=p.stdout.readline().decode())),flush=True)
time.sleep(60)
'''
        parent=subprocess.Popen([sys.executable,'-c',program,str(engine)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        messages=queue.Queue()
        def read():
            for _ in range(2):messages.put(parent.stdout.readline())
        threading.Thread(target=read,daemon=True).start()
        pid=None;handle=None;kernel=None
        try:
            pid=json.loads(messages.get(timeout=15))['engine_pid']
            ready=json.loads(messages.get(timeout=15))['ready']
            self.assertTrue(json.loads(ready)['ready'])
            if os.name=='nt':
                from ctypes import wintypes
                kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
                kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
                kernel.CloseHandle.argtypes=[wintypes.HANDLE]
                kernel.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT]
                handle=kernel.OpenProcess(0x1000|0x100000|1,False,pid);self.assertTrue(handle)
            def alive():
                if os.name=='nt':return kernel.WaitForSingleObject(handle,0)==258
                r=subprocess.run(['ps','-p',str(pid),'-o','stat=','-o','command='],capture_output=True,text=True)
                line=r.stdout.strip()
                return bool(line and not line.startswith('Z') and str(engine) in line)
            parent.kill();parent.wait(timeout=5)
            # parent.stdin is intentionally NOT closed: EOF cannot make the
            # native engine exit. Its platform parent-lifetime guard must do so.
            deadline=time.monotonic()+5
            while alive() and time.monotonic()<deadline:time.sleep(.02)
            self.assertFalse(alive(),'Native engine survived its real parent')
        finally:
            if parent.poll() is None:parent.kill();parent.wait(timeout=5)
            if pid is not None:
                if os.name=='nt' and handle:
                    if kernel.WaitForSingleObject(handle,0)==258:kernel.TerminateProcess(handle,127)
                    kernel.CloseHandle(handle)
                elif os.name!='nt':
                    r=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
                    if str(engine) in r.stdout:
                        try:os.kill(pid,signal.SIGKILL)
                        except ProcessLookupError:pass
            for stream in (parent.stdin,parent.stdout,parent.stderr):stream.close()

if __name__=='__main__':unittest.main()
