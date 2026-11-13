# Experimental macOS Metal GPU application

This is a direct TEST_ONLY GPU pilot, separate from BOINC project enrollment.
Read `METAL_BUILD.json`: `gpu_execution: false` means the host compiled it but
no GPU execution was validated. A CPU success never qualifies as GPU evidence.
The engine embeds its shader, retains the pinned exact 192-bit evaluator, and
uses bounded 32-bit atomic counters (at most 50 million points per packet).
The 64-bit high-product operation uses checked 32-bit partial products because
Metal does not provide C++ `unsigned __int128`. Host arithmetic checks alone do
not establish GPU correctness. There is no CPU fallback.
Signed input magnitudes are formed with unsigned subtraction before limb
multiplication; adversarial GPU checks retain negative inputs as well as the
positive bases used by packet evaluation.

## Test a kit on an authorized idle Mac GPU

Use Python 3.13+, extract the artifact ZIP and enclosed `metal-kit.tar.gz`, and
enter `metal-kit`. Enumerate Metal devices before selecting one explicitly:

```bash
python3 test_metal_client.py --list-devices
python3 test_metal_client.py --device-registry-id ID_FROM_LIST --destination metal-control-1
```

Expect PASS, three known controls, nine positions, zero new search coverage.
Keep the fresh output directory's results/checkpoints/receipts and the kit's
`METAL_BUILD.json`. Missing devices or shader/command errors are failures.
CI uses standard macOS runners only; no paid GPU runner is enabled automatically.
Apple Silicon is the first target. Intel/AMD Macs require separate hardware
acceptance; a compiled Intel host executable is not that acceptance.

## Full native build and GPU validation

Install Xcode command line tools, native Python 3.13+, git and Homebrew GMP.
From a fresh checkout of this repository, run:

```bash
python3 experiments/boinc-20261112/portable/metal/build_metal.py NEW_WORKSPACE
NEW_WORKSPACE/runtime/bin/scaling_gpu --list-devices
```

To run the full validation, build a second fresh workspace with the selected
device (do not overwrite the preserved first build):

```bash
python3 experiments/boinc-20261112/portable/metal/build_metal.py NEW_TEST_WORKSPACE --device-registry-id ID_FROM_LIST
```

The full path runs CPU prerequisites, 1,100 exact arithmetic cases, invalid
allocation rejection, real interruption/checkpoint recovery with independent
GMP acceptance, all 42 GPU packets against fresh GMP and the packaged smoke
test. Build and GPU acceptance states are recorded separately.

BOINC integration still requires an Apple GPU plan class, compatible stock
wrapper/Python packaging, reliable mapping of the allocated BOINC GPU to its
Metal registry ID and real download/upload/validation/restart tests. See official
[Metal plan-class support](https://github.com/BOINC/boinc/wiki/Specifying-plan-classes-in-XML#apple-silicon-gpus-with-metal)
and [Apple GPU naming](https://github.com/BOINC/boinc/wiki/Plan-classes).
This direct pilot does not claim that allocation mapping or BOINC acceptance.
