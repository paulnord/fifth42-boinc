"""Bounded Windows anonymous-pipe transport for the unchanged framed protocol."""
import json,queue,subprocess,threading,time

class EngineSession:
    def __init__(self,command,backend,deadline,environment=None):
        self.backend=backend;self.deadline=deadline;self.request_id=0;self.closed=False
        self.lines=queue.Queue(maxsize=4);self.stderr=bytearray();self.lock=threading.Lock()
        began=time.perf_counter()
        self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0,env=environment)
        self.readers=[threading.Thread(target=self._stdout,daemon=True),threading.Thread(target=self._stderr,daemon=True)]
        for reader in self.readers:reader.start()
        try:
            ready=self._line(min(deadline,time.monotonic()+30))
            if ready.get('ready') is not True or ready.get('backend')!=backend or ready.get('persistent') is not True:
                raise RuntimeError('Persistent engine startup handshake failed')
            self.ready=ready;self.startup_seconds=time.perf_counter()-began
        except BaseException:self.close();raise
    def _publish(self,value):
        while not self.closed:
            try:self.lines.put(value,timeout=.1);return
            except queue.Full:pass
    def _stdout(self):
        try:
            while not self.closed:
                data=self.process.stdout.readline(64*1024*1024+1)
                if not data:break
                if len(data)>64*1024*1024:
                    self._publish(RuntimeError('Engine response exceeds finite buffer allowance'));return
                if not data.endswith(b'\n'):
                    self._publish(RuntimeError('Engine closed an incomplete response'));return
                self._publish(data[:-1])
        except (OSError,ValueError):pass
        finally:self._publish(None)
    def _stderr(self):
        try:
            while not self.closed:
                data=self.process.stderr.read(4096)
                if not data:return
                with self.lock:
                    self.stderr.extend(data)
                    if len(self.stderr)>8192:del self.stderr[:-8192]
        except (OSError,ValueError):pass
    def _line(self,deadline):
        left=deadline-time.monotonic()
        if left<=0:raise TimeoutError('Persistent engine request deadline reached')
        try:value=self.lines.get(timeout=left)
        except queue.Empty:raise TimeoutError('Persistent engine request deadline reached') from None
        if isinstance(value,Exception):raise value
        if value is None:raise RuntimeError('Engine closed its output: '+self.stderr.decode(errors='replace'))
        return json.loads(value)
    def _write(self,data,deadline):
        errors=[]
        def write():
            try:
                view=memoryview(data)
                while view:
                    n=self.process.stdin.write(view)
                    if not n:raise BrokenPipeError('engine input closed')
                    view=view[n:]
            except (OSError,ValueError) as exc:errors.append(exc)
        writer=threading.Thread(target=write,daemon=True);writer.start();writer.join(max(0,deadline-time.monotonic()))
        if writer.is_alive():
            self.process.kill();writer.join(2);raise TimeoutError('Persistent engine write deadline reached')
        if errors:raise RuntimeError('Engine input failed') from errors[0]
    def run(self,packet,timeout=60):
        if self.closed:raise RuntimeError('Engine session is closed')
        self.request_id+=1;data=packet.encode()
        if len(data)>16*1024*1024:raise ValueError('Packet frame exceeds finite byte allowance')
        deadline=min(self.deadline,time.monotonic()+timeout);began=time.perf_counter()
        try:
            self._write(f'RUN {self.request_id} {len(data)}\n'.encode()+data,deadline)
            response=self._line(deadline)
        except BaseException:self.close();raise
        if response.get('request_id')!=self.request_id:raise RuntimeError('Engine returned a stale or mismatched request')
        return response,time.perf_counter()-began
    def close(self):
        if self.closed:return
        if self.process.poll() is None:
            try:self._write(b'QUIT\n',time.monotonic()+1)
            except (OSError,RuntimeError,TimeoutError):pass
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=2)
        self.closed=True
        for reader in self.readers:reader.join(2)
        for stream in (self.process.stdin,self.process.stdout,self.process.stderr):stream.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
