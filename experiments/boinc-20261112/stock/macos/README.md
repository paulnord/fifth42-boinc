# Private native Mac BOINC CPU and M4 Metal attachment

This session uses a new isolated database/project on Cabbage. It preserves all
earlier projects and production state. The CPU application ran on the owner's
physical M4/Tahoe system under BOINC 8.2.11: result 1 was accepted after fresh
GMP validation, three packets/nine positions. GPU acceptance is recorded
separately after the physical test; a queued GPU job is not a success claim.

## Connect the Mac

Start an authenticated SSH tunnel from the Mac, substituting your Cabbage SSH
host/address and the existing private lab path:

```bash
ssh -N -T -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:8765:/mnt/localstorage/pnord-fifth42-boinc-lifecycle-20261113/work/mac-transport/http.sock \
  pnord@CABBAGE_SSH_HOST
```

Keep it running. Check `http://127.0.0.1:8765/fifth42/` in a browser, then add
that exact project URL in BOINC and create a new private test account. BOINC
fetches the signed stock wrapper, native application and bundled Python runtime;
no Debian runtime or host Python installation is required. A new application
payload is about 41 MB. Keep the tunnel until upload and reporting complete.

The actual server has no host HTTP/database TCP listener. Only a mode-0600 Unix
socket in a private directory is reachable through SSH. Apache and MariaDB stay
on loopback in their private network namespace. No LAN service is enabled.

CPU version 1.30 uses `arm64-apple-darwin`. Corrected GPU version 1.41 uses
`arm64-apple-darwin__fifth42_apple_gpu_metal_m4`. The latter requires a numeric
Apple GPU allocation in the client's `init_data.xml`, exactly one physical
M4-family Metal device, and a 1,100-case GPU arithmetic self-test before packet
execution. Registry IDs are discovered and bound to that unique allocation;
there is no default-device fallback or multi-GPU claim. A missing allocation
or wrong device stops before science work. Intel GPU acceptance is not claimed.

Select the project and click Update after work is queued. If necessary, use
Activity / Use GPU always for the short GPU test and restore your preference
afterward. Correctly assigned GPU work should display one Apple GPU. Ready-to-
report work can be flushed with Update. Server canonical acceptance and fresh
GMP audit determine completion, not the GUI's completed-task display alone.

## Packaging and staging

`package.py` verifies the exact earlier CPU artifact and, for GPU, the accepted
arm64 Metal artifact. It fetches hash-pinned official stock wrapper 26019
universal and standalone Python 3.13.18. It materializes internal runtime file
symlinks in a ZIP with POSIX modes, which stock BOINC unpacks in the task slot.
The native macOS 26 workflow executes the real wrapper/runtime CPU path, tests
allocation/arithmetic rejection, and requires a real wrapper to refuse GPU work
when no BOINC GPU allocation exists. That negative CI check is distinct from
physical M4 GPU acceptance.

Examples use a fresh destination and an already prepared private stock project:

```bash
python3 package.py --kit-tar CPU_KIT.tar.gz --destination NEW_CPU_BUNDLE
python3 package.py --kit-tar CPU_KIT.tar.gz --backend gpu \
  --metal-artifact ACCEPTED_METAL_ARTIFACT.zip --destination NEW_GPU_BUNDLE
python3 stage.py --stock STOCK --bundle NEW_CPU_BUNDLE --version 1.30 --label MacCPU130
python3 stage.py --stock STOCK --bundle NEW_GPU_BUNDLE --version 1.41 --label MacMetal141
```

Inside the existing server namespace, export HERE, STOCK and RUNTIME, source
`$STOCK/env.sh`, run stock `php bin/update_versions --noconfirm --verbose`, and
query actual app-version IDs. Submit a bounded trusted manifest through stock
`submit.py` with the correct ID and `--engine BUNDLE/engine-identity`. For GPU,
also pass `--backend gpu`. That operator-supplied local file binds the Mac engine
hash while independent GMP remains on the Linux server. Worker claims never
select the trusted engine, backend or work manifest. Do not modify signed files
or reuse version/label destinations.

The bundled runtime expands to about 98 MiB. The Mac-only project's workunit
disk bound is 512 MiB to allow ZIP extraction, wrapper, bytecode and checkpoints.
Default Linux templates and other projects are preserved.

## Observed GPU assignment failure and correction

Version 1.40 used `<gpu_type>apple</gpu_type>`. In pinned BOINC source
`351ad42a102c2bbe70e33f7aa44c23ac6ac3db9c`, that selects the Apple capability
branch, but resource-type classification later recognizes `apple_gpu` instead.
The host usage can remain CPU, so client GPU allocation is absent and wrapper
`$GPU_DEVICE_NUM` remains literal. The first three client launch attempts failed
with status 195; no GPU result was accepted. The workunit was cancelled through
stock `cancel_jobs`, and the failures are retained.

Version 1.41 uses the stock generic lookup of canonical `apple_gpu`, one GPU,
512 MiB declared GPU RAM and an M4 CPU-model/client-version restriction. It does
not require OpenCL. The application verifies the actual Metal device and reads
BOINC's allocated number directly from `init_data.xml`; it refuses CPU metadata
or any absent, inconsistent or ambiguous allocation. The stock server is not
patched. This narrow profile is for the tested single-GPU M4 pilot, rather than
a general hardware capability policy. The GPU arithmetic tests retain negative
inputs, including the earlier Intel failure case.

## Session ownership and evidence

The tested service recipe is in `session/`. It assumes the previously prepared
Cabbage lab, read-only compiled stock dependencies/rootfs/science runtime, and
a separate writable `work/mac-server`. The live session started with equivalent
private recipe copies. `session/start.py --lab LAB` starts a four-hour user
service with two CPUs, 4 GiB RAM, no swap, 256 tasks, nice 19 and idle I/O.
It exports HERE/STOCK/RUNTIME for the nested shell. It never initializes over
an existing DB/project, never mounts production, and forwards no database port.

Inspect or stop only this owned unit on Cabbage:

```bash
systemctl --user status fifth42-boinc-mac-server-20261113
systemctl --user stop fifth42-boinc-mac-server-20261113
```

Private state is under `work/mac-server`; transport is `work/mac-transport`;
sanitized logs/hashes and native package evidence are in `evidence/mac-attachment`.
Keep account authenticators, client/server XML, signing keys and database files
outside Git and public archives. All fixtures remain TEST_ONLY with zero new
production coverage. No existing search, ledger, reservation, checkpoint,
production reporting, Ada or Boole process is changed by this session.
