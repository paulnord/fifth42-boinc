# Acceptance evidence checklist

This is a review checklist, not a declaration of passed tests. Preserve raw traces and distinguish **passed**, **failed**, **blocked**, and **not run** in the actual report.

| Gate | Required evidence |
|---|---|
| Installation | Actual stock server/client/supplied-wrapper version/commit or digest; isolated DB, project and client data directory; reproducible commands |
| Immutable inputs | Verify handoff assets, transport manifest/chunks/archive/extracted file hashes and packet catalog; fresh destination |
| CPU controls | Three named control fixtures through actual BOINC download/execute/upload; exact GMP result validation; client/server IDs and app hashes |
| Corruption | Uploaded truncated output, wrong packet identity and forged visit count rejected despite exit 0/file presence; strict types and complete per-task coverage |
| Recovery | Real committed first packet, durable receipt then checkpoint, actual client/app interruption and restart, wrapper recognizing checkpoint, exact completed-prefix replay accounting |
| Retry | Actual BOINC failed/lost attempt and retry/reassignment, shortened TEST_ONLY deadline, attempt provenance, one canonical accepted logical result |
| Upgrade | Real version A work in progress, immutable B files staged/signed via update_versions, new work actually downloaded B, executable hashes from both clients/results, oracle checks for A/B |
| Larger work | At least one representative larger packet end to end; full 42-packet CPU/GPU/GMP comparison recorded separately |
| GPU | Authorized idle device, plan class/resource request, allocated-device handling and architecture/build identity; otherwise precise blocker |
| Reproduction | Start, submit, status, drain and cleanup documented; no keys, passwords, generated binaries or bulky artifacts in Git |

## Specific failure probes worth retaining

- Output from correct packet but wrong cap; same apparent hit list is not proof that the cap is right.
- Missing/duplicated/reordered tasks, extra hits, lost negative residual, bool/float/string in integer fields, zero exit after partial result.
- Crash before receipt fsync, after receipt fsync but before checkpoint, and after checkpoint. Accept only a validated durable contiguous prefix. Recompute uncommitted work and never credit it twice.
- Corrupt/mismatched checkpoint or receipt: fail closed or explicitly restart safely; never skip work based on an unchecked integer prefix.
- GPU/engine subprocess termination when BOINC stops the application; no surviving compute processes.
- Two attempts return valid output for the same logical assignment: retained provenance, one accepted coverage increment.
- Result identity for an old attempt after version B is staged: validate against its actual version A identity, not whatever version is latest.

## Stock wrapper pitfalls

The upstream wrapper's checkpoint_filename is an application-written file: modification tells BOINC a checkpoint has completed. It does not itself make the science receipt durable. Fsync the receipt, then atomically write/rename and fsync the checkpoint and containing directory before announcing progress. The wrapper also checkpoints completed *wrapper tasks*, which is distinct from the completed-packet prefix within one long application task.

Declare multi_process for the Python driver plus native engine where needed and make each parent wait for its children. Engine is persistent framed I/O, not a raw-stdin executable: use engine_session.py. gmp_reference alone accepts raw packet stdin.

Application update_versions publishes version metadata and signs files, but uploading version B alone is not a demonstrated rollout. Existing work can remain version A; explicitly observe new scheduled work and downloaded binary identities. Keep immutable physical filenames per version and logical slot names stable. Do not use anonymous-platform app_info.xml as a replacement for testing server-delivered application versions.

The full 42-packet corpus contains 775,687,194 positions in 23 representative packets plus 19 tiny/controls. All replay is TEST_ONLY with zero new scientific coverage. Preserve per-packet 50,000,000, per-task 10,000,000, 4096 tasks and framed 16,777,216-byte limits as originally specified.
