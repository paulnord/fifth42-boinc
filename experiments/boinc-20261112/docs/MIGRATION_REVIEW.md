# Fifth42 BOINC migration review

Status: proposal only; no production cutover authorized. The prototype replays TEST_ONLY fixtures and earns **zero new scientific coverage**. A functioning native driver is not evidence of a functioning BOINC deployment.

## Fit and remaining scientific responsibility

BOINC is a plausible fit for durable queued work, host resource matching, bounded retries, application distribution and canonical result selection. It does not replace Fifth42's exact mathematics, region classification, coverage ledger, or independent verifier. Use BOINC for those standard lifecycle features rather than embedding the existing host-specific policy/controller machinery.

For this prototype, reconstruct every expected result independently with GMP and validate the actual uploaded artifact. For eventual production, recomputing every work unit centrally with GMP may erase the throughput benefit. Production needs a separately reviewed validation policy: independent redundant execution plus exact candidate verification and appropriate audits. Agreement between untrusted clients is not a mathematical proof of exhaustive search. Candidate verification proves reported hits, not absence of omitted hits. Do not silently substitute that weaker claim for the prototype's exact oracle checks.

A packet identity should bind canonical packet bytes, cap, arithmetic limits, task order, algorithm/source version and mathematical region. BOINC work-unit identity and physical file hashes must not be mistaken for complete scientific identity. Exact per-task and total visit counts, signed residuals, and complete hit sets are required. Reject booleans masquerading as integer counts, floating-point count encodings, duplicate tasks, extra/missing tasks, and incomplete outputs even after exit 0.

## Proposed cutover sequence (requires later owner approval)

1. Freeze a versioned specification of scientific region/cell numbering, exact input generation, caps, arithmetic limits and acceptance rules. Benchmark fixtures remain outside production namespaces permanently.
2. Stop issuing new legacy grants; let authorized old workers drain to durable receipt boundaries. Do not change existing deadlines or grants during this prototype.
3. After worker shutdown, reconcile local and replica journals and final checkpoints. A process exit or GitHub status alone is insufficient. Preserve failed, unsupported, uncertain and uncommitted intervals explicitly as unfinished.
4. Export an immutable, hashed ledger snapshot. Represent accepted evidence as half-open intervals qualified by cap and mathematical configuration, with provenance to native or analytic proof. Compute interval unions, not sums of cumulative counters. Preserve cap-42 versus cap-100 scope; do not promote weaker coverage or benchmark replay. A larger-cap proof may subsume smaller-cap work only after explicit equivalence checks of all other parameters.
5. Independently reconcile every issued/reserved interval against accepted intervals and unresolved intervals. Partition the intended scope into accepted, in-flight/uncertain, and unassigned; verify pairwise disjointness and full union. Resolve in-flight uncertainty before reissuing or treat its repetition as duplicate execution without duplicate credit.
6. Seed BOINC only from the verified unassigned partition. Unsupported near-zero regions must go to a compatible application or remain explicitly blocked; do not simply skip them while advancing a cursor. Keep native-limit/range guards unchanged.
7. Introduce a durable scientific-assimilation table keyed by immutable logical assignment and scope. A transaction accepts one canonical validated result and updates coverage once. BOINC may execute attempts more than once. Retries, late results, and host checkpoint recovery must never add the same logical coverage twice. Preserve rejected and superseded attempts for audit.
8. Run a small owner-approved canary before broad deployment. Compare accepted output and ledger changes independently. Retain the old journal snapshot and application files, and verify a restore before declaring cutover complete.

## Operations and recovery

Name a project operator and backup owner. Back up database, configuration, application metadata, immutable input/output provenance, scientific accepted-coverage ledger, and protected signing material. Store keys separately from public evidence. Test restoring database plus ledger to a consistent point and replay assimilation idempotently. Retain old application versions and their immutable physical filenames while any work or retries refer to them.

Drain means stop new assignment issuance, allow active bounded work to finish or checkpoint, wait for uploads/validation, then reconcile. Cleaning client directories, discarding queues or deleting versions is not a safe drain. Do not promise arbitrary checkpoint migration between hosts: same-slot restart may resume; reassignment may replay the whole work unit.

Rollback stops new BOINC issuance, drains/reconciles accepted work, exports a new accepted-ledger snapshot, and only then grants the still-unassigned remainder to legacy workers. Never run two independent authoritative allocators over the same scope.

## Performance and applicability

Measure native compute, driver startup, wrapper/client overhead, scheduling, transfers, uploads and validation separately. Batch millisecond packets into bounded work units. Choose a duration only after measured overhead and recovery-loss distribution, not by assuming fixed cell cost across regions. GPU allocation must use BOINC's actual device assignment and visibility, and must not compete with production. This Linux x86_64 baseline is not a Windows/macOS distribution claim.

Recommendation after the executed CPU evidence: **accept the CPU proof of fit; do not migrate production yet**. Actual server/client/wrapper execution, corruption rejection, durable recovery, retry canonicalization and A/B distribution passed; see `../REPORT.md`. Missing GPU hardware blocks CUDA acceptance. Portable packaging, fresh planning, authoritative coverage import, scalable validation and infrastructure-failure hardening remain prerequisites for a separately authorized cutover.

## Upstream references checked

Retrieved from BOINC's upstream wiki during review:
- ServerIntro: https://github.com/BOINC/boinc/wiki/ServerIntro
- CreateProjectCookbook: https://github.com/BOINC/boinc/wiki/CreateProjectCookbook
- WrapperApp: https://github.com/BOINC/boinc/wiki/WrapperApp
- Adding-app-versions: https://github.com/BOINC/boinc/wiki/Adding-app-versions

ServerIntro lists source builds, Debian/Ubuntu boinc-server-maker and marius311/boinc-server-docker. These are deployment options, not evidence that a particular current package/image has been built or tested. Record the actual installed upstream commit, package version or image digest. Avoid broad host/security changes to obtain a prototype.

## Validator infrastructure outages

The 2026-11-13 hook distinguishes explicit invalid scientific output (status 1)
from server configuration, storage, DB and oracle failures (transient status 3).
Actual oracle/DB-hook fault probes preserved and later accepted original uploads;
see [the lifecycle report](../stock/lifecycle/LIFECYCLE_REPORT.md). Stock BOINC may
leave these inconclusive and create another attempt; the probe used no-more-work
and an explicit upstream targeted recheck after recovery. Automatic retry timing,
full DB/service outages and operational recovery policy still need validation
before production. This does not establish production-scale resilience.
