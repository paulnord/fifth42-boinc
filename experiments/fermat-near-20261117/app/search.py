"""Exact Python CPU search and transport to the exact 512-bit CUDA search."""
import bisect
import ctypes
import os
import signal
import struct
import subprocess
from pathlib import Path
from protocol import MAX_HITS, checks, require


def cpu(task, budget=lambda: None):
    n, hi = task['exponent'], task['last_c']
    powers = [a ** n for a in range(hi + 1)]
    hits = []
    for c in range(task['first_c'], hi + 1):
        budget()
        radius = task['k_num'] * c ** (n - 3) // task['k_den']
        for a in range(1, c):
            target = powers[c] - powers[a]
            low = bisect.bisect_left(powers, target - radius, a, c)
            high = bisect.bisect_right(powers, target + radius, low, c)
            for b in range(low, high):
                delta = powers[a] + powers[b] - powers[c]
                if delta:
                    hits.append([a, b, c, str(delta)])
                    require(len(hits) <= MAX_HITS, 'Candidate buffer bound exceeded')
    return dict(hits=hits, a_values=checks(task))


def gpu(task, device, engine, prefix, capacity=MAX_HITS, timeout=300):
    n, hi = task['exponent'], task['last_c']
    source, output = Path(str(prefix) + '.bin'), Path(str(prefix) + '.gpu')
    def words(value):
        require(0 <= value < 2 ** 512, 'CUDA arithmetic width exceeded')
        return value.to_bytes(64, 'little')
    with source.open('wb') as stream:
        stream.write(struct.pack('<IIII', task['first_c'], hi, 16, capacity))
        for a in range(hi + 1):
            stream.write(words(a ** n))
        for c in range(task['first_c'], hi + 1):
            radius = task['k_num'] * c ** (n - 3) // task['k_den']
            words(c ** n + radius)  # prove the upper endpoint fits before launch
            stream.write(words(radius))
    environment = dict(os.environ, CUDA_VISIBLE_DEVICES=str(device))
    try:
        def parent_guard():
            parent = os.getppid()
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0 or os.getppid() != parent:
                os._exit(126)
        child = subprocess.Popen([str(Path(engine).resolve()), str(source), str(output)],
            env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            preexec_fn=parent_guard)
        try:
            _, error = child.communicate(timeout=timeout)
        except BaseException:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            raise
        require(child.returncode == 0, 'CUDA execution failed: ' + error[-1500:])
        require(output.stat().st_size <= 2 * 1024 * 1024, 'CUDA output size exceeded')
        rows = []
        seen = set()
        for line in output.read_text().splitlines():
            a, b, c = map(int, line.split())
            require(task['first_c'] <= c <= hi and 0 < a <= b < c, 'CUDA domain mismatch')
            require((a, b, c) not in seen, 'Duplicate CUDA candidate')
            seen.add((a, b, c))
            delta = a ** n + b ** n - c ** n
            require(abs(delta) * task['k_den'] <= task['k_num'] * c ** (n - 3), 'CUDA false positive')
            if delta:
                rows.append([a, b, c, str(delta)])
        require(len(rows) <= capacity, 'CUDA candidate buffer exceeded')
        return dict(hits=sorted(rows, key=lambda h: (h[2], h[0], h[1])), a_values=checks(task))
    finally:
        source.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
