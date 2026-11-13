# Cabbage lifecycle and Boole CPU/GPU results, 2026-11-13

All executed science work is **TEST_ONLY, with zero new production coverage**.
The private lab is stopped. Production ledgers, reservations, checkpoints, drivers
and reporting were not changed. Boole was attached only after the owner explicitly
selected it and requested both CPU and GPU tests; Ada remained excluded.

## Passed

| Test | Actual evidence |
|---|---|
| CPU native baseline | All 42 packets and fresh GMP passed; 25.20 seconds |
| Corrupt uploads | Wrong identity, forged count and truncated receipts rejected after exit 0; no canonical result |
| CPU checkpoint recovery | Real prefix 2 preserved across client stop/restart; two attempt identities, three final receipts |
| A/B release | A remained bound to its original version while B was staged; new work downloaded B, with actual file hashes checked |
| Failed-attempt retry | BOINC abort and reassignment of the same workunit; retry recomputed nine positions from prefix 0 and selected one canonical result |
| Representative CPU work | 49,491,764 positions accepted through the real client/upload/GMP path |
| Oracle and DB-hook outages | Hook exited transient status 3; original uploads remained eligible and were accepted after dependencies returned |
| Boole native CPU | Controls plus 49,491,764-position workunit downloaded, executed, uploaded and accepted |
| Boole native GPU | Controls plus the same representative workunit downloaded, executed with BOINC's NVIDIA allocation, uploaded and accepted |
| GPU restart | Client quit at durable prefix 1; GPU process/context disappeared; restart resumed exactly at 1 and completed with two attempt identities |
| GPU native equivalence | All 42 packets and fresh GMP passed on Boole; 17.47 seconds |
| Direct regressions | 23 tests passed, including malformed results, checkpoint corruption, transient errors, and allocated-device handling |

Boole's separate project had canonical results 1–5: CPU controls, CPU representative,
GPU controls, GPU representative, GPU recovery. CPU app-version ID was 2 (1.10),
GPU ID 1 (1.20, `fifth42_cuda`). Every downloaded application file matched its
staged SHA256. See [sanitized records](../../evidence/cabbage-lifecycle-20261113/summary.json)
and [download hashes](../../evidence/cabbage-lifecycle-20261113/application-downloads.json).

## Actual platform and transport

The server remained the pinned Debian 13 stock BOINC build, upstream
`351ad42a102c2bbe70e33f7aa44c23ac6ac3db9c`, supplied wrapper 8.3.26019.
Boole ran stock Ubuntu 26.04 BOINC **8.2.9+dfsg-1build1**, extracted into a private
directory without package installation or maintainer scripts. Its runtime used
native Ubuntu `/usr` libraries in a private namespace; it did **not** require a
Debian client runtime. CPU and GPU application versions used one BOINC client.

The owner-authorized RTX 3060 was idle before testing. The GPU engine was compiled
from the pinned published numerical source with CUDA **13.3.73**, GCC/G++ 15,
`-arch=sm_86`; driver **595.99.02**. GPU engine SHA256:
`4cd44fb3ec9cc1e111a168e9db914e7fd7e065c67b8795b71979b388e55aef91`.
Its CUDA runtime is statically linked. This is a private Ubuntu 26.04/SM86 build,
not a universal Linux or arbitrary-GPU compatibility claim.

The unchanged native GPU engine selects logical device zero. The science driver
sets `CUDA_VISIBLE_DEVICES` from the wrapper's actual `$GPU_DEVICE_NUM` before
starting it; it never silently defaults to physical GPU zero. Missing or ambiguous
allocation fails closed. The actual hardware test had one GPU (allocated device 0);
nonzero-device environment mapping was unit-tested, not multi-GPU hardware-tested.

An authenticated OpenSSH Unix-socket forward connected the private namespaces.
Both project URLs stayed `127.0.0.1:8765`; sockets were mode 0600 beneath private
directories. No HTTP, database or GUI RPC port was exposed to the LAN. Database
traffic was not forwarded. Existing host SSH was used without configuration changes.

Each test scope capped CPU at two cores, RAM at 4 GiB, swap at zero, and ran at
nice 19. The native client requested one CPU; the GPU plan requested one NVIDIA
device and 0.1 average CPU. Both client instances quit through BOINC RPC, all
owned services/tunnels stopped, and no GPU compute process survived shutdown.
The resumed Cabbage server peaked at 180.90 MiB; Boole's first client instance
peaked at 122.6 MiB according to its systemd journal.

## Infrastructure behavior and diagnosed failures

Previously every validator exception permanently rejected the result. Explicit
scientific failures now return 1; missing/malformed trusted configuration, failed
DB access, unreadable storage, oracle crashes/timeouts/bad oracle output and other
server exceptions return BOINC's transient status **3**. Subprocess arguments
containing potential DB credentials are not printed. An accepted audit is written
only after scientific checks and fresh independent GMP succeed.

The stock backend leaves transient results **inconclusive (state 4)**, not
necessarily unchecked (state 0). The first test assertion incorrectly expected 0;
the raw failure and corrected continuation are retained. Stock BOINC can also
raise its target replication count and issue another attempt while no canonical
result exists. That occurred on the first oracle probe. Later probes used
`nomorework` to avoid assigning redundant execution during the injected outage.
Original uploads were retained and accepted; no SQL result states were edited.

After restoring dependencies, the test invoked upstream
`script_validator --wu_id ID --one_pass` for an explicit operator recheck. This is
not evidence of immediate automatic recovery under BOINC's ordinary retry timing.
Faults targeted the hook's DB connection/oracle, not a full MariaDB service outage.

CUDA 12.8 failed against Ubuntu 26.04's newer math headers; installed CUDA 13.3
compiled and passed without patching CUDA, system headers or the numerical source.
The first Ubuntu namespace layout could not add mount points beneath the read-only
host root; a temporary root with explicit read-only Ubuntu system mounts fixed it.
Both failures are archived. BOINC logged expected internet/DNS diagnostics in the
network-isolated namespace. Tiny GPU fixtures also generated a bad FLOP-ratio
credit warning; scientific validation passed. Their estimates/BOINC credits are
not meaningful production sizing or coverage measures.

## Scope at this archive point

Windows/macOS application builds are separate follow-up work and are not claimed
here. This run did not prove cross-host timeout reassignment, multi-GPU selection,
GPU suspend/abort beyond clean quit/restart, full DB crash/restore, scalable
production verification, or public/LAN enrollment security. Native source and
all original exact arithmetic, framing, packet/task and candidate limits remain
unchanged. See [Boole testing instructions](BOOLE_TESTING.md).
