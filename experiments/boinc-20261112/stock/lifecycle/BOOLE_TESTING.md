# Testing the native Ubuntu CPU/GPU client on Boole

The standard BOINC client obtains signed science application versions from the
project server. No per-host source edits or custom work allocator are required.
These instructions describe the private test harness, not a production service.
Use a fresh isolated project/client directory for an exact replay; preserve
completed projects and do not overwrite their immutable application files.

## Recorded locations and components

* Cabbage lab: `/mnt/localstorage/pnord-fifth42-boinc-lifecycle-20261113`.
* Cabbage local lifecycle project: `work/stock-verify`.
* Cabbage server for Boole: `work/boole-server` (separate database/project).
* Boole private client: `/home/pnord/boinc-fifth42-client-test-20261113/work/client`.
* Boole runtime: `work/runtime`, Ubuntu BOINC 8.2.9 packages extracted with
  `dpkg-deb -x`, with no postinst or privileged host installation.
* Boole CUDA build: `work/native/bin/scaling_gpu`; compiler command below.
* Recipes are in this directory's `recipes/`; acceptance drivers are
  `run_suite.py` and `run_remote.py`. The scripts are specific to this test lab's
  paths and UID/GID 1330. Read them before adapting to another computer.

The previous Debian root was copied during preparation but was not used by the
native Ubuntu client. The namespace uses Ubuntu `/usr`, `/etc`, `/sys` read-only,
an empty temporary root/home/mount tree, the private work directory and the
explicitly authorized NVIDIA device nodes. Only loopback networking exists.

## Build and direct checks

On Boole, after fetching and verifying the pinned science bundle in a private
directory, the successful GPU command was:

```bash
/usr/local/cuda-13.3/bin/nvcc -ccbin /usr/bin/g++-15 -std=c++17 -O3 -arch=sm_86 \
  work/native/native/src/scaling_gpu.cu -o work/native/bin/scaling_gpu
CUDA_VISIBLE_DEVICES=0 python3 work/native/colab_bench.py \
  --backend gpu --repeats 1 --max-seconds 180 --verify-gmp
```

The explicit device in this **direct numerical check** was owner-authorized and
idle. BOINC-delivered GPU execution instead obtains the allocated device from
its wrapper. Do not turn the direct command into a hardcoded production device.
For a different GPU/toolchain, build an appropriate immutable version/plan class
and validate it rather than assuming this SM86/Ubuntu build applies.

Direct science/validator regressions on the server runtime:

```bash
export FIFTH42_RUNTIME=/absolute/path/to/runtime
python3 -m unittest discover -s experiments/boinc-20261112/tests -v
```

## End-to-end test sequence

1. Verify resource ownership and an idle authorized GPU; keep existing searches
   untouched. Start with a new project/client namespace and private directories.
2. Initialize the Cabbage server with the stock scripts. Install the narrowly
   scoped `fifth42_cuda.xml` as `project/plan_class_spec.xml` for the tested build.
3. Stage CPU with `stage_application.py --backend cpu --label BooleCPU --build B
   --version 1.10`, and GPU with `--backend gpu --label BooleGPU --build B
   --version 1.20`; provide the usual `--stock` and `--runtime` arguments.
4. Run stock `php bin/update_versions --noconfirm --verbose`. Query actual
   app-version IDs; never assume the IDs from the archived run.
5. Create a private BOINC test account. Transfer its account XML over authenticated
   SSH into the new client directory with mode 0600. Never include it in Git/logs.
6. Start `socket_relay.py --listen-unix /pilot/server-http.sock --target-port 8765`
   inside the server namespace. Use OpenSSH `-R remote_socket:local_socket` with
   `StreamLocalBindMask=0177`, verified host keys and private parent directories.
   The client-side relay binds only its namespace's `127.0.0.1:8765` and connects
   to the forwarded Unix socket. No DB/RPC forwarding or LAN listener is needed.
7. Start the native Ubuntu client with the provided namespace/client recipes,
   one CPU and GPUs enabled. Apply the two-CPU/4-GiB user-service limits and the
   900-second runtime safety bound used by `run_remote.py`.
8. Submit uniquely named controls with the stock `submit.py`, the actual CPU or
   GPU app-version ID, build B, and matching `--backend cpu|gpu`.
9. Require server canonical acceptance, fresh GMP audit, and matching actual
   downloaded file hashes. Then test the representative `ada-upper-w0-b0` fixture.
10. For GPU restart, submit controls with `--pause-after 1 --pause-seconds 60
    --packet-delay 2`. Save the real checkpoint/receipts, quit the client, verify
    no science process/context remains, and restart with the same client data.
    Require `resumed_prefix=1`, two attempt identities and exactly three receipts.
11. Drain, RPC-quit, stop owned relays/tunnel/server, verify shutdown, and retain
    sanitized evidence plus private DB/client state separately.

The recorded host driver was invoked as:

```bash
FIFTH42_LAB=/mnt/localstorage/pnord-fifth42-boinc-lifecycle-20261113 \
  python3 source/experiments/boinc-20261112/stock/lifecycle/run_remote.py
```

It is a one-shot acceptance driver against a prepared fresh server; rerunning it
unchanged against completed work would correctly hit duplicate-submission guards.
For interactive checks in an already-running owned namespace, use `nsenter` with
`--user --mount --net --pid --preserve-credentials` and the recorded helper paths.
Preserving credentials is required for rootless namespaces with `setgroups` denied.
Use only your own test namespace, never a production process.

No Debian client runtime is required. Other operating systems need their own
compiled engine/wrapper/runtime packaging and native acceptance before support
can be advertised. These particular Linux binaries are not Windows/macOS clients.
