# Four133 package acceptance, 2026-11-16

The target is four signed 133rd powers summing to 42. All work in this report
is TEST_ONLY and earns no new scientific coverage. No exact solution was found.

## Native packages

Linux x86_64 and Apple Silicon macOS packages execute the original mathematical
engine through stock BOINC wrapper 26019 and bundled CPython 3.13.18. The
mathematical source hash is frozen in `UPSTREAM.json`; Mac's allocation/RSS
adapter has its own recorded build hash and an allocation-limit self-test.

The native suite checks both sign patterns/reflections, independent modular
enumeration against a Cartesian oracle, 61 nonempty modular-collision controls,
fresh GMP final arithmetic, durable checkpoint/restart, changed-log rejection,
forged omitted candidates, trusted server assignment, and retryable oracle
failure. Version 1.02 adds a kernel CPU-time budget and a SIGSTOP/SIGCONT test
that pauses beyond a one-second budget without consuming that CPU budget.

## Actual BOINC client and server

The isolated private project registered application `four133`, CPU plan
`four133_cpu_1`, version 1.01 (database app-version ID 14). A dedicated Linux
BOINC 8.0.4 client ran with one advertised CPU, no GPUs, a one-CPU cgroup quota,
one-GiB memory cap, and no swap. No physical Mac BOINC acceptance is claimed.

The server's own database marked both final work units successful, valid and
canonical, exit status zero:

| Result | Work | Independent validation |
| --- | --- | --- |
| 26 | `four133-domain-acceptance-20261116` | Original production guards, B=5,000,000, old=4,000,000, normalized sum 4,206,972, gap 1, both original sieve moduli; 150,946 pair entries replayed, zero modular candidates |
| 27 | `four133-linux-final-20261116` | Four small synthetic collision controls, sixteen assigned gaps, 61 modular candidates checked with GMP, zero exact hits |

Native logs, manifests, accepted audits and database receipts are retained in
`linux-boinc-20261116/`. Audits certify only their assigned gap regions. They
do not certify an enlarged full box or an admitted production campaign.

The actual client was stopped after its first durable chunk and restarted.
Result 25 records `resumed_tasks=1`, BOINC delivery and all four completed tasks.
Direct execution of the trusted database/GMP hook accepted that receipt. The
first validator daemon had been launched from the project root; stock
`script_validator` expects a log directory and could not resolve its
`../bin/four133_validate` hook. Its recorded validation failure is retained.
The packaged launcher fixes the working directory, and fresh results 26/27
were accepted through the normal validator daemon. No validation state was
manually changed to obtain those successful receipts.

Earlier retained controls exposed a missing Linux `libzip.so.4` (result 23)
and the Linux Python runtime exceeding a 512-MiB disk allowance (result 24).
The package now includes the pinned library and copyright notice. Work templates
allow two GiB for archive, unpacked runtime, checkpoints and output. The stock
result-template reader also requires its tags on separate lines; those templates
were corrected before the accepted controls. `allocation-result24.json` belongs
to that earlier disk-limit run.

Version 1.02 retains the accepted native engine and BOINC delivery contract;
it changes the driver watchdog from elapsed wall time to CPU time so ordinary
BOINC suspension and duty cycling do not invalidate healthy work. Its bundled
wrapper and pause behavior are tested independently in the native suite. The
recorded full client/server receipts above were obtained with version 1.01.

The dedicated pilot client and validator were stopped after receipt archival.
Existing fifth-power applications, authoritative search ledgers and user Mac
preferences were not changed by this packaging test. The Mac package is ready
for a separate physical-client control before admitting a production campaign.
