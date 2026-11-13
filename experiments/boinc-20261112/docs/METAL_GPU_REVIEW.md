# Metal GPU prototype acceptance, 2026-11-13

Every distributed CPU application kit was executed on a native Linux, Windows,
Apple Silicon Mac or Intel Mac runner. Each original kit passed 12 direct tests
and all 42 packets against freshly executed independent GMP. The additive Metal
driver option was subsequently checked with 14 direct tests on all four targets
in [run 43494510922](https://github.com/paulnord/fifth42-boinc/actions/runs/43494510922).
Cabbage's complete local regressions passed 26 tests. Real BOINC CPU and CUDA
download/execution/upload/validation/recovery on Boole is recorded separately;
Windows/macOS BOINC attachment has not been performed.

## Mac GPU outcome

| Target | Outcome |
| --- | --- |
| arm64 macOS 15, `Apple Paravirtual device`, unified memory | Full Metal GPU suite passed |
| Intel macOS 15, `Apple Paravirtual device`, non-unified memory | Exact negative-input arithmetic failed; no accepted GPU kit |
| Physical M-series or Intel/AMD Mac GPU | Not yet tested |

Accepted arm64 code commit: `06bc5bbf6916c731f703292f348e5aa8e1225986`.
Native workflow: [43495401468](https://github.com/paulnord/fifth42-boinc/actions/runs/43495401468).
Successful arm64 job: `132127054099`; Intel failure: `132127054536`.

The arm64 run compiled the host engine and offline shader/library, then passed:

- 1,100 GPU arithmetic cases, including negative inputs and limb boundaries.
- Explicit invalid-device rejection and real candidate-capacity overflow rejection.
- Real parent-death cleanup with the engine's input pipe kept open externally.
- A killed application at durable prefix 1, followed by recovery with two
  attempts, exactly three receipts and fresh GMP acceptance.
- All 42 GPU packets matching expected counts/hits and fresh independent GMP.
- The actual packaged three-control/nine-position smoke test.

The full GPU/GMP comparison elapsed 33.783 seconds on that runner; this is not
a physical Mac performance comparison. Host-only common-evaluator tests also
passed 1,100 arithmetic and 100,025 high-product cases, plus all 42 packet/GMP
comparisons. Host-only checks are not counted as GPU execution.

## Failures and scope

Metal requires explicit constant address spaces for program globals; the initial
source failed shader compilation until those declarations were adapted. Raw
subprocess diagnostics and independent offline compilation were added to expose
that error clearly.

The Intel GPU arithmetic result for `(0,-1)` had an incorrect negative-power
limb. The same code passed the arm64 Metal suite. An unsigned-magnitude rewrite
still failed on Intel and was reverted. The cause has not been established;
this report does not attribute it to a compiler or driver without proof. All
negative-input checks remain enabled. The draft PR preserves the failure and
does not publish an accepted Intel GPU application.

The source retains bounded exact 192-bit integer formulas, translated types and
address spaces, with 64x64 high-product implemented via bounded 32-bit partial
products. GPU counters use 32-bit atomics because validated packets have at
most 50 million iterations. Counts come from actual iterations and are checked
against trusted expectations/GMP. Shaders are embedded in the engine identity.
Explicit registry IDs select devices; there is no CPU fallback.

No paid GPU runner was enabled. No production workers, ledger, reservations,
checkpoints or reporting were modified. All pilot services remain stopped.
All fixtures are TEST_ONLY and contribute zero new search coverage.

## Download and test

The [accepted arm64 artifact](https://github.com/paulnord/fifth42-boinc/actions/runs/43495401468/artifacts/14072245829)
ZIP SHA256 is `ca9a9fe5e8012ac1f8a08261eb4f9a32eafd7f7d7a6c758fa539da8d80a42710`.
Extract it and its enclosed `metal-kit.tar.gz`, enter `metal-kit`, then use
Python 3.13+ on an authorized idle Mac GPU:

```bash
python3 test_metal_client.py --list-devices
python3 test_metal_client.py --device-registry-id ID_FROM_LIST --destination metal-control-1
```

Expected: PASS, three controls, nine positions, zero new coverage. Keep the
output directory and `METAL_BUILD.json`. See [full native build and testing
instructions](../portable/metal/METAL_TESTING.md) for the 42-packet/GMP path.
The online artifact expires under Actions retention; original bytes, checksums,
success/failure logs and resource measurements are preserved in Cabbage's
private `metal-client-evidence` directory and its archive.

Before a BOINC Mac GPU pilot, verify physical hardware, map BOINC's allocation
to a Metal registry ID, package a stock wrapper and explicit Python runtime,
stage signed immutable Apple-GPU application versions and run real project
download/upload/validation/restart acceptance. Official BOINC documents
[Metal capability requirements](https://github.com/BOINC/boinc/wiki/Specifying-plan-classes-in-XML#apple-silicon-gpus-with-metal)
and [Apple GPU plan-class names](https://github.com/BOINC/boinc/wiki/Plan-classes).
