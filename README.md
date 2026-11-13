# Fifth42 BOINC prototype

A reproducible, **TEST_ONLY CPU/CUDA prototype** for running the Fifth42 search
through an unmodified stock BOINC server, client and wrapper.

## Start here

- [Prototype and science reproduction](experiments/boinc-20261112/README.md)
- [Full results and limitations](experiments/boinc-20261112/REPORT.md)
- [Stock BOINC setup and lifecycle commands](experiments/boinc-20261112/stock/README.md)
- [Cabbage private-container pilot and setup fixes](experiments/boinc-20261112/stock/CABBAGE_PILOT.md)
- [CPU lifecycle and Boole native CPU/GPU results](experiments/boinc-20261112/stock/lifecycle/LIFECYCLE_REPORT.md)
- [How to test the Boole client](experiments/boinc-20261112/stock/lifecycle/BOOLE_TESTING.md)
- [Native Linux, Windows and macOS CPU application kits](experiments/boinc-20261112/portable/CLIENT_KITS.md)
- [Experimental Mac Metal GPU results and testing](experiments/boinc-20261112/docs/METAL_GPU_REVIEW.md)
- [Acceptance review](experiments/boinc-20261112/docs/ACCEPTANCE_REVIEW.md)
- [Migration recommendation](experiments/boinc-20261112/docs/MIGRATION_REVIEW.md)
- [Raw test evidence](experiments/boinc-20261112/evidence/)

## Verified scope

The isolated Linux CPU prototype exercised real BOINC execution, checkpoint
recovery, failed-attempt retry, A-to-B application upgrade and rejection of
three corrupted uploads. It includes independent GMP correctness checks and
reproducible setup scripts. Test fixtures contribute **no new search coverage**.

The later Cabbage lifecycle suite and Boole native Ubuntu CPU/GPU tests passed,
including GPU checkpoint recovery and full 42-packet GPU/GMP equivalence. The
private test used authenticated SSH Unix-socket forwarding without LAN exposure.
Native Linux x86_64, Windows x86_64, macOS arm64 and macOS Intel CPU application
kits build and pass direct correctness tests on their respective native CI
runners. Real Windows/macOS BOINC attachment and multi-GPU hardware tests remain
separate acceptance steps; these kits require host Python 3.13 or newer.

This is **not a production deployment or public volunteer service**. Portable
application packaging, production coverage migration and scalable
validation remain work for a later stage. The prototype's full central GMP replay
is a correctness gate, not an economical production validator. Validator
infrastructure failures now defer via BOINC status 3; full service outages and
automatic retry timing still need operational testing.

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
