# Fifth42 BOINC prototype

A reproducible, **TEST_ONLY CPU proof of concept** for running the Fifth42 search
through an unmodified stock BOINC server, client and wrapper.

## Start here

- [Prototype and science reproduction](experiments/boinc-20261112/README.md)
- [Full results and limitations](experiments/boinc-20261112/REPORT.md)
- [Stock BOINC setup and lifecycle commands](experiments/boinc-20261112/stock/README.md)
- [Cabbage private-container pilot and setup fixes](experiments/boinc-20261112/stock/CABBAGE_PILOT.md)
- [Acceptance review](experiments/boinc-20261112/docs/ACCEPTANCE_REVIEW.md)
- [Migration recommendation](experiments/boinc-20261112/docs/MIGRATION_REVIEW.md)
- [Raw test evidence](experiments/boinc-20261112/evidence/)

## Verified scope

The isolated Linux CPU prototype exercised real BOINC execution, checkpoint
recovery, failed-attempt retry, A-to-B application upgrade and rejection of
three corrupted uploads. It includes independent GMP correctness checks and
reproducible setup scripts. Test fixtures contribute **no new search coverage**.

This is **not a production deployment or public volunteer service**. GPU testing,
portable application packaging, production coverage migration and scalable
validation remain work for a later stage. The prototype's full central GMP replay
is a correctness gate, not an economical production validator. Transient validator
infrastructure failures also need separate treatment before production.

## Provenance and isolation

The prototype was exported without numerical changes from local source commit
`1fe6516fda73c1f2148faaa36876a5e27af2c54d`, following the
[pinned handoff](https://github.com/paulnord/fifth42/blob/d891e96fb4f77f95da6cfd0ad34380af486786e3/handoffs/20261112/DOT_BOINC_HANDOFF.txt).
Science inputs and engine sources are downloaded from the explicitly pinned
upstream revision in `scripts/prepare_science.sh`; they are not silently taken
from the current production branch.

`SOURCE_MANIFEST.json` preserves the original import's file hashes; subsequent
setup fixes and the Cabbage recipe are recorded in this repository's Git history.

The original directory layout is retained so the tested scripts and evidence
remain unchanged. This repository does not alter the existing
[paulnord/fifth42](https://github.com/paulnord/fifth42) repository, production
workers, NFS grants, checkpoints or reservations.

No new license is asserted here; upstream components retain their respective
terms. Review licensing before broader redistribution.
