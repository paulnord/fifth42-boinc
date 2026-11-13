# Cabbage / physical M4 private attachment, 2026-11-13

This is TEST_ONLY work with zero new production coverage. Both physical M4
CPU and corrected Metal GPU controls passed under BOINC and were accepted by
the stock server after fresh independent GMP validation.

## Observed results

The Mac reported BOINC 8.2.11, Apple M4, Darwin 25.6.0 and one Apple GPU with
Metal support 4 and about 12 GiB available GPU memory. The owner identifies the
system as M4 / Tahoe 26.6.2. It needs no Debian runtime; the application is a
native arm64 Mach-O engine with a bundled macOS Python runtime.

CPU version 1.30, app-version ID 1, ran workunit
`mac_m4_cpu_control_20261113`. Result 1 was uploaded, reported, marked successful
and canonical, and accepted after fresh Linux GMP checking: three packets,
nine positions, matching the pinned control manifest. Acceptance audit:
`work/mac-server/validator-audit/1.json`.

GPU version 1.40 failed three attempts before science execution, exit status
195. The wrapper passed literal `$GPU_DEVICE_NUM`. Source inspection found the
stock server's `apple` capability branch did not set Apple resource type in its
later classification step. The old workunit was cancelled with stock
`bin/cancel_jobs --name mac_m4_metal_control_20261113`; failed results 2–4 remain
in the new private database. No successful GPU result is inferred from them.

GPU version 1.41, app-version ID 3, uses canonical `apple_gpu`, and its launcher
reads BOINC's actual GPU allocation from `init_data.xml`. It requires exactly
one physical M4-family GPU, checks the registry identity and runs 1,100 exact
GPU arithmetic cases before the control. No implicit device-zero assignment is
used. Workunit `mac_m4_metal_control_141_20261113`, result 5, was dispatched at
22:44:35 UTC and accepted at 22:45:00 UTC. It became canonical with successful
outcome, valid state and exit status zero. The result records BOINC GPU number
0, Metal name `Apple M4`, registry ID `4294968192`, all 1,100 arithmetic checks
passed, and three completed packets/nine positions. The science driver reported
0.108 seconds; the wrapper's child process used about 0.190 CPU seconds. These
are tiny control timings, not throughput measurements. Acceptance audit:
`work/mac-server/validator-audit/5.json`.

The initial 1.41 policy also had `os_regex=Darwin`. Scheduler diagnostics showed
that stock BOINC tests that expression against OS *version*, here `25.6.0`.
It rejected requests before dispatch. The redundant rule was removed while
1.41 remained unsent; the registered Mac platform already restricts the OS.
The subsequent real-client request obtained a true Apple GPU assignment and
completed successfully. Signed application payloads were preserved.

## Checks and retained failures

- Native macOS 26 workflow [43518832722](https://github.com/paulnord/fifth42-boinc/actions/runs/43518832722)
  passed on commit `290d327e9f803842a0cc3dcdaccf3abd4807e168`: actual stock
  wrapper/runtime CPU execution, allocation/arithmetic refusal boundaries and
  actual-wrapper refusal when no BOINC GPU allocation exists. CI GPU refusal
  is a negative check, not a physical GPU computation claim.
- All 24 existing server/validator/lifecycle regression tests passed locally
  in 2.478 seconds using the pinned runtime. The three new Metal allocation and
  arithmetic boundary tests also passed in native CI.
- Earlier workflow 43517339065 failed its refusal harness because BOINC had
  redirected the diagnostic to `stderr.txt`. The corrected harness captures
  that file and still requires failure before science output.
- The separate synthetic stock-scheduler regression reproduced the old alias
  as CPU and the corrected 1.41 plan as one `apple_gpu`. It ran for 66.948
  seconds, consumed 2.764 CPU seconds, peaked at 661.8 MiB and stopped cleanly.
  It performed no science. Earlier harness attempts exposed missing tmpfs
  mount parents, unstable app-version ID ordering, bare `&` in BOINC RSS URLs,
  missing CPU-version/OpenCL-memory fixture data and feeder refresh timing.
  Those harness failures and final corrected recipe are preserved separately.
- The runtime ZIP expands to about 98 MiB. The Mac-only workunit disk bound is
  512 MiB, allowing extraction, wrapper, bytecode and checkpoints.

## Exact live session and resources

Lab root: `/mnt/localstorage/pnord-fifth42-boinc-lifecycle-20261113`.
Source checkout: `mac-cpu-source`, branch `feat/mac-cpu-attachment-20261113`.
Private project and DB: `work/mac-server`; transport: `work/mac-transport`.
CPU/old GPU/corrected GPU bundles: `work/mac-server/client-bundle`,
`work/mac-server/metal-bundle`, `work/mac-server/metal-bundle-141`.
Evidence: `evidence/mac-attachment`. Private credentials, signing keys and DB
files are excluded from the curated evidence archive and Git.

The service started at 21:32:52 UTC and has a four-hour lifetime, ending at
01:32:52 UTC on November 14 (19:32:52 Central on November 13). Its limits are
two CPUs, 4 GiB RAM, no swap, 256 tasks, nice 19 and idle I/O. At the 22:39 UTC
snapshot it used 438,460,416 bytes, peaked at 447,967,232 bytes, and had consumed
about 5.34 CPU seconds; private project storage was 905 MiB. Measurements can
increase while the service runs. The live server is left up for the requested
Mac attachment; clean shutdown of this session is not yet claimed.

The live private copies in `recipe/mac-server.sh`, `mac-server-wait.py` and
`start-mac-service.py` implement the versioned `session/` recipe. The latter
exports HERE/STOCK/RUNTIME for nested shells. Namespace administration uses:

```bash
mac_anchor=$(pgrep -f '^python3 /recipe/mac-server-wait.py$')
nsenter --target "$mac_anchor" --user --mount --net --pid \
  --preserve-credentials bash
export HERE=/source/experiments/boinc-20261112
export STOCK=/pilot/mac-server RUNTIME=/pilot/science/runtime
source "$STOCK/env.sh"
```

Inside that shell the deployed GPU registration/submission commands were:

```bash
python3 "$HERE/stock/macos/stage.py" --stock "$STOCK" \
  --bundle "$STOCK/metal-bundle-141" --version 1.41 --label MacMetal141
(cd "$STOCK/project"; php bin/update_versions --noconfirm --verbose)
python3 "$HERE/stock/submit.py" --stock "$STOCK" --runtime "$RUNTIME" \
  --manifest "$STOCK/metal-bundle-141/controls.json" \
  --name mac_m4_metal_control_141_20261113 --app-version-id 3 \
  --build A --backend gpu --engine "$STOCK/metal-bundle-141/engine-identity"
```

These are historical commands, not commands to repeat against already staged
versions or submitted workunits. IDs were queried from this project's DB.

Apache and MariaDB listen only on private namespace loopback. The host has no
HTTP 8765 or database 3306 listener. The SSH tunnel in README.md transports HTTP
through a mode-0600 Unix socket. Services and DB are not exposed to the LAN.

## Further work

The owner can restore BOINC Manager's Activity / Use GPU based on preferences
after the control. Keep the tunnel for any separately requested follow-up work.
The accepted control establishes this particular M4 CPU/GPU path; sustained
GPU throughput, larger workunits, interruption/checkpoint behavior and other
physical Mac GPUs still need separate validation.

Broader Mac support requires a general plan-class hardware policy and physical
testing beyond this single M4. Intel Metal correctness is unresolved in the
separate prototype PR; no Intel GPU package is accepted. Secure LAN clients
still require an authenticated HTTPS project endpoint, hardened DB credentials
and permissions, restricted enrollment, operational signing-key protection,
resource/rate limits and maintained server packaging. The current private
namespace and SSH tunnel remain the supported transport for this pilot.
