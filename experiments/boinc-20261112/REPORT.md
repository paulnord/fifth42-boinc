# Fifth42 BOINC prototype: executed results

This report preserves the original 2026-11-12 evidence. Later Cabbage lifecycle,
validator-outage fixes and Boole native CPU/GPU execution are recorded separately
in [the 2026-11-13 report](stock/lifecycle/LIFECYCLE_REPORT.md).

**Recommendation: accept the CPU proof of fit; adjust the packaging and validation
cost model before considering a production cutover.** BOINC successfully supplied
the queue, signed application releases, client execution, uploads, recovery and
retry/canonical-result handling. There is no custom replacement scheduler.
Production Ada/Boole/Cabbage and their accepted coverage were not changed.

Every fixture is **TEST_ONLY, with zero new scientific coverage**.

## Actual BOINC results

| Test | Server evidence | Outcome |
|---|---|---|
| Three signed controls | WU 2 `controlA2`, canonical result 4, application 1.00 | Passed: cap 100/+12, cap 42/+12, cap 2951/−2002; 3 packets, 9 positions, fresh independent GMP |
| Client interruption/restart | WU 3 `recoveryA`, canonical result 5, application 1.01 | Passed: client recognized checkpoint, stopped at durable prefix 2, restarted at exactly 2 and completed 3 |
| Application upgrade | WU 4 `upgradeB`, canonical result 6, application 1.02 | Passed: B staged while A work was active; client downloaded B, old work remained A; both accepted against same oracle |
| Failed attempt/retry | WU 5 `retryB`, aborted result 7, canonical result 12 | Passed: first attempt committed one real packet then was aborted; BOINC issued retry, which recomputed from 0 and was accepted once |
| Wrong identity upload | WU 6, result 8 | Rejected despite worker exit 0; no canonical result |
| Forged visit count upload | WU 7, result 9 | Rejected despite worker exit 0; no canonical result |
| Truncated receipt list upload | WU 8, result 10 | Rejected despite worker exit 0; no canonical result |
| Representative larger input | WU 9 `representativeB`, canonical result 11 | Passed: `ada-upper-w0-b0`, cap 42, 49,491,764 positions, fresh GMP |

The retry was an actual BOINC **failed-attempt** test, not an expired-host test.
The test workunits used 600-second TEST_ONLY report deadlines. A requested
120-second CLI override did not override the template's 600 seconds; the actual
DB values are retained. Host-loss timeout/reassignment to a second computer is
not claimed. Checkpoints were preserved on the same client, not migrated between
hosts. The retried logical job accepted one result; its first packet was genuinely
recomputed. Worst-case recomputation for that tiny workunit is its full 9 positions.

The CPU driver durably writes receipts before the checkpoint. Recovery result 5
retains two receipts from the first attempt and the third from the resumed
attempt. BOINC's client log explicitly records checkpoint recognition. The test
used bounded pauses and inter-packet delays so the stock wrapper's whole-second
mtime polling could observe the changes; no work or count was fabricated.

Version 1.00 was the initial control release. Version 1.01 (physical label A2,
mathematical build A) added wrapper command-line passthrough and multiprocess
metadata needed for the lifecycle probes, without modifying old release files.
Version 1.02 (B) has an identifiable driver build change, unchanged mathematics,
and immutable new filenames. All six downloaded A2 files and all six B files were
SHA256-compared to their actual staged versions, independently of worker-reported
hashes. See `evidence/boinc/upgrade/`.

## Independent numerical and adversarial checks

The full supplied **42-packet CPU run and freshly executed independent GMP oracle
passed** in 31.84 seconds, including the representative 23 packets containing
775,687,194 positions. This is direct native evidence, separate from the BOINC
runs above. CUDA is **not run**: this isolated environment has no NVIDIA device or
CUDA toolchain, and no production GPU was borrowed. Pending on an explicitly
available test GPU: compile for its architecture; register a stock NVIDIA plan
class and CPU/GPU resource request; verify `$GPU_DEVICE_NUM` against device
visibility rather than assuming device 0; run all 42 CPU/GPU/GMP comparisons and a
representative BOINC GPU job; verify suspend/abort ownership and measure total
pipeline cost. None of those hardware checks is inferred from the CPU pass.

The final direct/unit suite has 13 distinct test methods on Python 3.12 and 3.13.5,
including multiple corruption variants. Earlier review logs include repeated
inherited executions; these are not additional independent tests. The suite tests
real process interruption, uncommitted suffix recomputation, corrupt checkpoints,
strict count types, missing/reordered/duplicate receipts, and trusted DB mapping.
DB mapping unit probes use mocks and are not represented as BOINC execution.

## Timing and workunit sizing

A representative native replay took **0.338 seconds**; the bounded driver took
0.363 seconds and BOINC reported 2.021 seconds elapsed for that task. Its
assignment-to-report interval was 22 seconds, including transfer, polling and
queuing alongside other tests. That interval is not a pure network measurement.
The corresponding server validation log spans about 1.37 seconds.

For the tiny B controls, native work was 0.000797 seconds, driver elapsed 0.0217
seconds, BOINC elapsed 2.042 seconds, and assignment-to-report 24 seconds including
new application downloads. The first B release transferred roughly 5.4 MB of
wrapper/engine/scripts; later jobs reused those application files. The local
loopback network is not a volunteer-network benchmark. Recovery/retry intentional
sleep time must not be treated as useful numerical runtime.

**Do not create one network job per millisecond packet.** A next private pilot
should measure groups targeting several minutes of native work (initial candidate
5–15 minutes), retaining packet-prefix checkpoints, and tune against measured
worker speed and real transfer/validation cost. A useful rule is native work at
least 20 times fixed scheduling/startup overhead for a sub-5% fixed-overhead target.
The present 42-packet fixture bound is a prototype limit, not evidence for a final
production batch size. The current validator hook treats infrastructure exceptions as permanent result
rejection. Before production it must distinguish transient DB/oracle/service
failures and return BOINC's transient-validation status (3), with outage tests;
otherwise a healthy worker can be blamed for a server fault. This is a known
prototype hardening gap, not a passed resilience test.

Full GMP re-execution on the server is intentionally strong
for this prototype but can become the production bottleneck; a scalable science
validation policy needs separate review, not silent weakening of checks.

## Reproduction, limitations and cleanup

See `stock/README.md` for the pinned stock components and short build, start,
release, submit, status, drain and cleanup commands. See `docs/MIGRATION_REVIEW.md`
for coverage import, cap separation, draining, ownership and rollback requirements.
The implementation uses stock server release 1.6.3, source commit
`351ad42a102c2bbe70e33f7aa44c23ac6ac3db9c`, supplied wrapper 8.3.26019 and client
8.0.4. The upstream configure package number is 8.3.0; these are different
upstream numbering schemes, not unrecorded source substitutions.

Initial setup faults are preserved: an output-template formatting error left
WU 1 unfinished, and the first two WU 2 attempts were rejected because the
script-validator launch directory made its hook unavailable. Correcting the
stock launch directory allowed BOINC's retries to succeed. WU 1 was explicitly
canceled; it was not counted as accepted. No scientific failure was hidden by
editing result rows into success.

The development package relies on Linux x86_64, host Python and recent shared
libraries. It is not yet a portable public volunteer client. Fresh planning and
import of the real coverage ledger remain migration work, not part of this
prepared-packet replay prototype. Windows/macOS, GPUs, internet enrollment,
multiple-host failure, server crash recovery and a full production-scale load test
are not established here. The reusable initialize/start/release/submit/client recipe was also rerun against
a separate fresh database and project (reusing the compiled stock binaries):
`recipe_control`, WU 1/canonical 1, passed fresh GMP at 22:08:32 UTC. That
independent smoke result is in `stock/fresh-recipe-smoke.json`. A second generic
helper job with nonempty science arguments also passed (canonical 2,
`stock/fresh-recipe-args.json`); it verified the helper's wrapper argument forwarding. The final combined clean build script is documented
separately from commands actually executed; do not interpret an unrerun combined
script as a second clean-build result.

After capturing results, the original test client was put in no-more-work mode,
quit cleanly, and the validator and stock service stack were stopped. The isolated
database and evidence remain available for inspection. No credentials, signing
private keys, generated executables or raw account files are included in Git.
