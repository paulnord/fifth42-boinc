# DOT: native Windows CPU and NVIDIA GPU BOINC acceptance

Paul authorizes testing the fifth42 project's new `fermat_near` clients on this
lab PC. Carry out the tests with available tools. If this ChatGPT session cannot
execute local PowerShell, give Paul the required commands in short batches.

The application searches bounded TEST_ONLY controls for powers 4–32 with
`0 < |a^n+b^n-c^n| <= n*c^(n-3)`. This is client acceptance, not a production
search or performance benchmark. Linux CPU/CUDA and physical M4 CPU/Metal
controls have passed. Native Windows CI passed CPU arithmetic, checkpoint
tests, stock-wrapper execution, CUDA compilation, and missing-device rejection.
Positive Windows GPU hardware acceptance remains to be done here.

## PC and packages

1. Record Windows edition/build/architecture, CPU, GPU model, NVIDIA driver,
   and BOINC version. Use Windows x64. To test both clients, use an NVIDIA GPU
   with compute capability at least 7.5 (for example GTX 16 series or RTX) and
   driver at least **572.61**, compatible with that GPU and OS. AMD/Intel GPUs
   can test the CPU client; this CUDA package cannot run on them. Report that
   limitation. Do not change lab GPU drivers without separate authorization.
2. Use official 64-bit Windows BOINC. If installation is needed, use the normal
   interactive installation; a Windows service installation does not provide
   the intended GPU test environment. Paul supplies any admin credentials
   privately. The science packages bundle Python and the CUDA runtime; do not
   install Python, GMP, a compiler, or a CUDA toolkit on this PC.
3. Repository: https://github.com/paulnord/fifth42-boinc/pull/8,
   branch `feat/fermat-near-boinc-20261117`. The signed packages already staged
   on Cabbage are CPU **1.40**, app-version ID **20**, and CUDA **1.50**, ID **21**.
   They came from source commit `87525472325cc949f469ce334d1bd81ddbc7ba98` and
   native CI https://github.com/paulnord/fifth42-boinc/actions/runs/44139867748.
   Let stock BOINC download them. Do not use anonymous-platform `app_info.xml`
   or replace downloaded executables.

## Connect an isolated test client

Preserve existing BOINC clients, projects, data, and preferences. Create a fresh
private directory such as `%LOCALAPPDATA%\Fifth42BOINC-test-20261117`, and use
local GUI RPC port **31429** after checking it is free. Do not expose GUI RPC
or the project server on a LAN interface.

On the PC, keep this SSH connection running in a separate terminal:

```powershell
ssh -N -T -o ExitOnForwardFailure=yes -L 127.0.0.1:8765:/mnt/localstorage/pnord-fifth42-boinc-lifecycle-20261113/work/mac-transport/http.sock pnord@cabbage.valpo.edu
```

Use the normal SSH host-key check; Paul enters his credentials privately. This
requires campus connectivity or the campus VPN. The project URL is exactly:

`http://127.0.0.1:8765/fifth42/`

Before attaching, verify server readiness:

```powershell
ssh pnord@cabbage.valpo.edu "python3 /mnt/localstorage/pnord-fifth42-boinc-lifecycle-20261113/recipe/windows-near-control-20261117.py doctor"
```

The private server and validator were refreshed at **11:53 AM CST November 17,
2026**, for eight hours (until approximately **7:53 PM CST**). If unavailable,
report the readiness error and ask the Cabbage session to refresh this private
pilot. Do not reconfigure public networking or another BOINC project.

Put this configuration in the test directory before starting the client:

```xml
<!-- cc_config.xml -->
<cc_config><options><ncpus>1</ncpus><skip_cpu_benchmarks>1</skip_cpu_benchmarks></options></cc_config>
```

```xml
<!-- global_prefs_override.xml -->
<global_preferences><run_if_user_active>1</run_if_user_active><run_gpu_if_user_active>1</run_gpu_if_user_active><cpu_usage_limit>100</cpu_usage_limit><suspend_cpu_usage>0</suspend_cpu_usage><max_ncpus_pct>100</max_ncpus_pct><work_buf_min_days>0</work_buf_min_days><work_buf_additional_days>0</work_buf_additional_days></global_preferences>
```

Launch `boinc.exe` interactively with the actual absolute data path:

```powershell
$testData = Join-Path $env:LOCALAPPDATA 'Fifth42BOINC-test-20261117'
& 'C:\Program Files\BOINC\boinc.exe' --dir $testData --allow_multiple_clients --gui_rpc_port 31429 --no_info_fetch
```

Control only this instance using `boinccmd.exe --host 127.0.0.1:31429` and its
private `gui_rpc_auth.cfg` password. Read the password locally without printing
it. Create a new private pilot account through the tunneled project site or
BOINC's account commands, then attach this client to the exact URL above.
Do not publish account authenticators, passwords, account XML, or the complete
client-state file. Do not reuse or request the Mac's credentials.

Find the actual new Windows host ID after its first scheduler request:

```powershell
ssh pnord@cabbage.valpo.edu "python3 /mnt/localstorage/pnord-fifth42-boinc-lifecycle-20261113/recipe/windows-near-control-20261117.py hosts"
```

Match OS, CPU, and recent request time. Use that numeric ID below in place of
`HOST_ID`; do not type the placeholder literally.

## Run and verify both backends

Queue CPU controls first, then request a project update from the private client:

```powershell
ssh pnord@cabbage.valpo.edu "python3 /mnt/localstorage/pnord-fifth42-boinc-lifecycle-20261113/recipe/windows-near-control-20261117.py queue --host HOST_ID --backend cpu"
```

This queues two small controls: powers 4–32 over c=2–200, and a nonempty wide
integer case at n=30, c=966 containing (a,b,c)=(860,965,966). Wait for uploads
and reporting. Query server validation, not merely the local task exit:

```powershell
ssh pnord@cabbage.valpo.edu "python3 /mnt/localstorage/pnord-fifth42-boinc-lifecycle-20261113/recipe/windows-near-control-20261117.py status --host HOST_ID"
```

Repeat the queue command with `--backend gpu` on a compatible NVIDIA PC.
Require GPU detection in the BOINC log, a real allocated NVIDIA device, and
CUDA version 1.50 execution. A CPU fallback does not establish GPU acceptance.

For each backend, also run a real quit/restart control:

```powershell
ssh pnord@cabbage.valpo.edu "python3 /mnt/localstorage/pnord-fifth42-boinc-lifecycle-20261113/recipe/windows-near-control-20261117.py queue --host HOST_ID --backend cpu --restart"
```

Use `--backend gpu --restart` for the GPU control. It pauses 120 seconds after
the first of two chunks. During that pause, confirm `checkpoint.json` and
`chunk-000.json` exist in the active task's private slot and
`fraction_done.txt` contains 0.5. Quit only this test client through its GUI RPC
port, then restart it with the same directory and arguments. Preserve slot
files. Require the server audit to report `resumed_tasks >= 1`. Run CPU and GPU
restart tests separately so the intended task and checkpoint are identifiable.

The queue command is idempotent for the same host/backend/run label. If a
diagnosed fix requires another attempt, supply a new `--run-label`, such as
`20261117b`; preserve the first attempt's evidence.

## Acceptance and cleanup

Pass requires each result to have `accepted: true` in server status: finished
server state, success outcome, validate_state=1, exit_status=0, and its own
canonical result ID. The independent GMP validator checks completeness and
exact arithmetic. The wide-match control must include the expected hit, CPU
and GPU candidate records must agree, and restart audits must show resumption.
Six accepted results are expected when both backends and restart tests run.

Save hardware/driver/BOINC versions, host and result IDs, app versions, useful
client logs, server audits, and payload hashes in a private evidence folder.
Ask the Cabbage session to archive server evidence in the PR. On failure report
the exact stage and error; do not weaken validation or claim hardware success
from compilation or missing-device rejection.

Finally set no-more-work for this project in the private client, finish uploads
and reporting, quit only the private test instance, close its SSH tunnel, and
preserve evidence. Leave the lab PC's existing workloads intact.

Reference: [BOINC client configuration](https://github.com/BOINC/boinc/wiki/Client-configuration),
[boinccmd](https://github.com/BOINC/boinc/wiki/Boinccmd-tool),
[Windows installation](https://github.com/BOINC/boinc/wiki/Installing-on-Windows),
[CUDA 12.8.1 release notes](https://docs.nvidia.com/cuda/archive/12.8.1/cuda-toolkit-release-notes/index.html).
