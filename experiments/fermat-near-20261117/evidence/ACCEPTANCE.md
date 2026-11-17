# Boole CPU and CUDA client acceptance, 2026-11-17

All **26 actual BOINC results** were successful, valid and canonical in the
stock server database, with exit status zero. The private native Ubuntu BOINC
8.2.9 client ran on Boole's Ryzen 9 5950X and NVIDIA RTX 3060. The existing
fifth42 search was left running during these short client checks.

| Check | CPU 1.00 | CUDA 1.10 |
| --- | --- | --- |
| Every exponent 21–32, c=2..1000, K=n | 12 accepted results | 12 accepted results |
| Quit and restart after first durable chunk | Accepted, resumed_tasks=1 | Accepted, resumed_tasks=1 |
| CPU/GPU complete candidate lists | Identical for every exponent | Identical for every exponent |
| Downloaded application files | All hashes match signed packages | All hashes match signed packages |

The server independently replayed **11,991,120 `(a,c)` positions** with GMP,
including the restart controls, and verified 92 returned candidate occurrences.
The same mathematical candidates are checked on both backends; these are not
92 distinct discoveries. All assigned zero-result regions were also replayed.
The eight native tests passed on Boole with CUDA enabled, including wider than
256-bit values, rational cutoff equality, repeated bases, deliberate CUDA output
overflow, omitted-candidate rejection, durable recovery and missing-oracle retry.

Raw work manifests, exact uploaded results, GMP audits, result stderr, database
receipts, build identities, download hashes and the native test log are under
[boole-20261117](boole-20261117/). Uploaded bytes match the hashes in the accepted
audits. Account XML, client state, signing keys and the database are excluded.

These tests establish delivery, execution, restart, upload and independent
acceptance for the bounded CPU/CUDA clients. They are not a throughput comparison,
a large-height lattice search, or a production campaign. BOINC FLOP estimates
remain uncalibrated and its stock validator logged FLOP-ratio warnings; these
did not alter scientific validity or canonical acceptance. Credit was disabled.
The private test client, its SSH relay and the new validator were stopped after
the tests. Existing search processes and the separate Mac service were preserved.
