# Physical M4 CPU / Metal comparison

This bounded session uses the existing private Mac project and native versions
1.30 (CPU, app-version ID 1) and 1.41 (M4 Metal, ID 3). It replays the exact
pinned 42-packet catalog, 789,435,567 candidate positions per task, with three
trials each in CPU/GPU alternating order. `run.py` waits for canonical fresh GMP
acceptance before submitting another task, avoiding CPU/GPU trial overlap.
Every task remains TEST_ONLY and creates no production coverage.

The CPU engine defaults to one thread. The GPU trial uses one Apple GPU and
declares 0.1 CPU; this is not an all-core CPU comparison. Both native packages
are already cached from successful controls. Each task receives a fresh slot
and must report resumed prefix zero. GPU tasks repeat the 1,100-case arithmetic
self-test before science. This overhead is included in BOINC elapsed time and
excluded from the science driver's elapsed time.

`run.py` records per-task driver time, sum of packet engine/RPC times, GPU kernel
time, reported BOINC elapsed and CPU time, independent acceptance, then medians
and CPU-time/GPU-time ratios. Its timer has a 600-second bound for each awaited
result. Server-side GMP validation and transfer/reporting latency are outside
the Mac application timings. Tiny control results are not throughput evidence.

`rpc_policy.py` temporarily adds stock server `next_rpc_delay=20` to this private
project, allowing the subsequent tasks to advance without repeated manual
Updates. It removes the setting after the controller completes/fails, on a stop
signal, or after 30 minutes. It refuses to replace an existing RPC policy and
records restoration in `evidence/mac-benchmark/RPC_POLICY.json`. The first
project Update is still needed to deliver the schedule to the Mac.

The live session uses private copies in the lab's `recipe/` directory. The
controller and RPC helper enter only the existing Mac namespace. The controller
has a 50% CPU/512-MiB/no-swap/32-task limit and a 30-minute lifetime; the helper
has 25% CPU/128-MiB/no-swap/16-task limits and a 31-minute lifetime. Main server
limits remain two CPUs and 4 GiB. No production or other host is involved.

These scripts are exact session tools with fixed project paths and immutable
job names. They require the already prepared full42 manifest and trusted Mac
engine identities. Inspect existing work before invoking them; they refuse
pre-existing later trials rather than overwrite evidence. Repeated experiments
need new names and a separate reviewed record.
