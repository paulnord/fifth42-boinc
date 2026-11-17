# BOINC Fermat near-miss CPU and CUDA client pilot

Application `fermat_near` runs bounded searches for

```
0 < |a^n + b^n - c^n| <= K * c^(n-3),  0 < a <= b < c.
```

Exponents 4–32 are supported, with client acceptance focused on every exponent
21–32. Both residual signs, repeated bases and scaled triples are included.
The default is the paper's score cutoff `|r| >= 1`, where
`r = n*c^(n-3)/(c^n-a^n-b^n)`; this sets **K=n** for each exponent.
`--k P/Q` selects a fixed positive rational K instead. No floating-point
arithmetic selects candidates or decides whether they meet the cutoff.

This first client pilot uses complete bounded enumeration, with quadratic work
in the largest c. It is not the large-height lattice planner discussed for a
future campaign. Work is TEST_ONLY, c is capped at 20,000, each chunk has at
most 256 c rows, and each work unit has at most two million `(a,c)` comparisons.
These guards deliberately keep client correctness tests small. No production
ledger or claim of new mathematical discovery is attached to these receipts.

## Backends and validation

CPU version 1.00 uses Python's arbitrary-precision integers and exact binary
search of each b interval. CUDA version 1.10 searches those intervals on the
allocated NVIDIA GPU using unsigned 512-bit integers. Python prepares exact
power tables and checks every returned GPU candidate with arbitrary-precision
arithmetic. Width and output-buffer overflow abort the chunk before it can
commit. The current immutable CUDA package targets the tested SM86 hardware.

Both versions declare one BOINC CPU; CUDA also requires one NVIDIA GPU.
The wrapper's allocated GPU number controls visibility. An absent allocation
or literal, unexpanded `$GPU_DEVICE_NUM` is rejected. No GPU is assumed when
the CPU package runs.

The server independently enumerates every assigned region using **GMP and
monotonically advancing interval endpoints**, a different implementation from
the Python/CUDA binary searches. It compares the complete candidate lists,
including zero-result regions. Dropping candidates therefore fails validation.
Missing server infrastructure defers validation for retry. Server-side work,
host and application-version records select the trusted manifest and backend.

Chunk files are fsynced before the checkpoint advances. Restarts bind the saved
prefix to the exact work manifest and application build, recheck the committed
prefix hash, and recompute an interrupted chunk. The CPU watchdog counts CPU
time. CUDA subprocess execution additionally has a 300-second wall timeout;
very long suspension during a native CUDA invocation remains outside this
short pilot's acceptance scope.

## Reproduce numerical tests

```
g++ -O2 -std=c++17 native/gmp_oracle.cpp -lgmpxx -lgmp -o gmp_oracle
NEAR_GMP="$PWD/gmp_oracle" python3 -m unittest discover -s tests -v
```

On the tested CUDA host:

```
/usr/local/cuda-13.3/bin/nvcc -ccbin /usr/bin/g++-15 -std=c++17 -O2 \
  -arch=sm_86 --cudart=static native/near_gpu.cu -o near_gpu
NEAR_GMP="$PWD/gmp_oracle" NEAR_GPU="$PWD/near_gpu" \
  python3 -m unittest discover -s tests -v
```

The tests cover all exponents, a separate triple-loop oracle, native GMP replay,
the exact `13^5+16^5-17^5=12` threshold, repeated bases, values wider than 256
bits, CUDA buffer overflow, durable restart, altered checkpoints, forged omitted
candidates and missing-oracle retry behavior. The GPU cases are explicitly
skipped unless a CUDA executable is selected; a CPU-only pass is not GPU evidence.

## BOINC packaging and private submission

`packaging/build.py` bundles hash-pinned stock BOINC wrapper 26019, relocatable
CPython 3.13.18 and the wrapper's Linux libzip dependency. Neither host Python
nor a privileged BOINC installation is required on the client. Packages target
Linux x86_64 and Apple Silicon macOS. The accepted Boole CPU 1.00 and CUDA 1.10
versions remain immutable, built from commit
`51b06054719b3f8eb48206ba07fe96f43e632781`. Updated Linux builds use 1.01/1.11;
Mac CPU and Metal builds use 1.20/1.30. Mac hardware acceptance is separate from
native CI build and wrapper checks. Windows and other GPU architectures require
their own native package and acceptance work.

```
python3 packaging/build.py NEW_CPU_BUNDLE --backend cpu
python3 packaging/build.py NEW_GPU_BUNDLE --backend gpu --gpu-engine ./near_gpu
python3 app/make_work.py --exponents 21 --last-c 1000 \
  --unit-id UNIQUE_CONTROL --min-score 1 --output NEW_MANIFEST.json
```

An optional `--assets DIRECTORY` reuses the downloaded assets only after their
pinned SHA-256 checks pass. Keep bundles immutable once signed and registered.
CPU/GPU packages use different version numbers so stock scheduling preserves
the requested backend.

Inside an existing private stock project environment, prepare a mode-0600 JSON
config with `mysql_command` (argument array), `database`, `gmp_reference`
(server-native GMP oracle path), `audit_directory`, and empty
`application_versions` and `workunits` dictionaries. Host assignment must already
be enabled. The installed source paths must remain available to the validator.

```
python3 packaging/server.py --project PROJECT --config PRIVATE_CONFIG stage NEW_CPU_BUNDLE
python3 packaging/server.py --project PROJECT --config PRIVATE_CONFIG stage NEW_GPU_BUNDLE
python3 packaging/server.py --project PROJECT --config PRIVATE_CONFIG \
  submit NEW_MANIFEST.json --host HOST_ID --version ACTUAL_REGISTERED_VERSION_ID
python3 packaging/server.py --project PROJECT --config PRIVATE_CONFIG validate
```

The stock server and the Boole client use private loopback network namespaces
joined by authenticated SSH Unix-socket forwarding. The included Boole recipes
take a fresh private data directory and an existing extracted native BOINC
runtime. They are pilot recipes for the tested Linux/NVIDIA host, not general
installation scripts. Wrap clients and validators in finite resource supervisors.
Account XML, authenticators, signing keys and database files stay outside Git.

## Apple Silicon Mac packages

The CPU package uses the same exact arbitrary-precision search. The Metal
package implements the interval search with sixteen 32-bit limbs and checked
carry/borrow operations; its shader uses neither floating point nor 64-bit
shader integer operations. The current physical-client profile requires one
BOINC-allocated Apple M4-family GPU and BOINC 8.2.11 or newer. The executable
refuses absent allocation, multiple devices and other GPU families.

```
python3 packaging/build.py NEW_MAC_CPU --backend cpu
python3 packaging/build.py NEW_MAC_METAL --backend metal
```

Build on a native arm64 Mac with Xcode command-line tools. Native CI compiles
the Metal shader and runs real stock-wrapper CPU controls with bundled Python.
Shader compilation is not physical M4 arithmetic acceptance. On an actual M4,
set `NEAR_METAL` to `NEW_MAC_METAL/payload/bin/near_metal` alongside `NEAR_GMP`
to execute the separate Metal arithmetic tests. Those tests include all powers
4–32, wide integers, cutoff equality and candidate-buffer overflow.
