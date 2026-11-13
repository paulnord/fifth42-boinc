# Native CPU application test kits

These artifacts contain the native CPU engine, bounded Python application driver,
known controls, build identities and native test evidence. They are experimental
**TEST_ONLY application kits**, not installers for the BOINC core client or a
claim of real Windows/macOS BOINC attachment. Standard BOINC supplies its own
platform-specific core client; operators subsequently stage compatible application
versions through the project's normal signing/release mechanism.

## Try a downloaded kit

Install Python 3.13 or newer, extract the downloaded artifact and its enclosed
`client-kit.tar.gz`, enter `client-kit`, and use a new output directory:

```text
python test_client.py --destination control-run-1
```

On systems whose command is `python3`, use that instead. Expected output ends
with `PASS: native CPU application, 3 control packets, 9 positions`. Retain
`control-run-1/result.json`, receipts and checkpoint. Do not reuse a destination
or promote these fixtures into production coverage. The kit does not require GMP
at runtime; CI independently built and executed the GMP oracle before packaging.

`BUILD.json` records platform, architecture, compiler, pinned numerical source,
the process/I/O portability overlay and hashes. `NATIVE_TEST_EVIDENCE.json` records
the full 42-packet comparison. Numerical/frame/range limits are unchanged.
The full CI comparison has a 600-second overall bound to accommodate variable
hosted-runner speed; individual request bounds and all comparisons remain active.

## Native build prerequisites

Linux: C++17 GCC, Python, git and GMP development headers. macOS: Xcode command
line tools, Python, git and Homebrew GMP. Windows x86_64: MSYS2 UCRT64 GCC/GMP and
native Python. CI uses native hosted runners, never emulation to claim acceptance.
Run `portable/build_native.py NEW_WORKSPACE --compiler COMPILER` from this source
tree to acquire the pinned bundle, apply only the platform I/O/parent-lifetime
overlay, build, run direct tests/full fresh GMP comparison, and produce a kit.

Windows uses fixed-width oracle coordinates (its C++ `long` is only 32-bit),
binary framed standard I/O and bounded pipe-reader/writer threads;
its checkpoint replacement uses a flushed temporary file and Windows write-through
rename. macOS uses a bounded parent-lifetime monitor; Linux retains its original
parent-death signal guard. These are process/filesystem checks, not a power-loss
durability or arbitrary-filesystem certification.

## Before BOINC enrollment on another platform

Obtain a compatible stock BOINC wrapper, choose and package a supported Python
runtime or explicit host dependency, stage immutable platform-specific files and
job paths, and run real download/execution/upload/validation/restart checks against
the private project. Keep host ownership and GPU selection explicit. Windows and
macOS CPU kits do not imply CUDA/Metal support. No production migration or public
project enrollment is authorized by these artifacts. Upstream component terms
continue to apply; no new license is asserted by this kit.
