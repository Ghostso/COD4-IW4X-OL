# EX-038 IIPS Loader Chain and `0x8189FEC` Upstream Caller

## Final Classification

```text
IIPS_LOADER_CALLER_UNCONFIRMED
IIPS_INIT_CALLER_UNCONFIRMED
IIPS_EXPORT_RESOLUTION_UNCONFIRMED
8189FEC_RUNTIME_SOURCE_UNCONFIRMED
IIPS_LAST_MODULE_BEFORE_FATAL_PARTIAL
NO_NEW_EXECUTION_NODE
```

The `-q` run confirmed `iips.dll` is loaded and the IIPS init error window
appears, but this round did not produce a new upstream `LoadLibrary` /
`GetProcAddress` caller or a runtime site that produces `0x8189FEC`.
Export execution and DllMain success/failure remained unobserved.

## Runtime Observation

Independent copy:

```text
工具/EX035_DIR
```

Launch:

```text
codoMP_client_shipRetail.exe -q
```

Observed in the parameter-matrix observer:

```text
iips.dll module loaded
iipsinit Environment List Box window present
WIN_IIPS_INIT_ERROR / 8189FEC fatal dialog present
```

A second, shorter observer run did not catch `iips.dll` in its final
module snapshot, so the loader is timing-sensitive or the load is brief
before the fatal path. The load itself is still runtime-confirmed by the
broader observer.

## Loader Caller

No LdrLoadDll/LoadLibrary/GetProcAddress hook was stable without altering
module load timing. The actual caller address for `iips.dll` was not
captured this round.

## `GetResourceManagerII`

```text
resolution: NOT OBSERVED
caller: NOT OBSERVED
return: NOT OBSERVED
```

Export presence in `iips.dll` is not evidence of runtime resolution or
use.

## `iipsinit` Window Creation

The `iipsinit` window was observed again, but the window-creation caller
was not captured. No `CreateWindowExA`, `CreateWindowExW`, or dialog API
hook was installed.

## Error UI Caller

The `WIN_IIPS_INIT_ERROR` display caller is still inside a packed/VM
region as far as static raw data indicates. No runtime caller was
captured.

## Module Timeline

Detailed first-seen timeline was not produced because the observer
sampled module lists periodically rather than hooking the loader. The
available evidence from previous runs shows project modules load before
the fatal UI, including:

```text
TenProxy.dll
TenRpcs.dll
GameRpcs.dll
tcj.dll
GDPLoader.dll
policyprobe.dll
GbSpy.dll
iips.dll
```

`iips.dll` is the last IIPS-land module observed before the fatal UI in
the successful catch. That is a partial timeline, not a causal chain.

## DllMain / Dependency Status

```text
iips.dll DllMain success/failure: NOT OBSERVED
ifs2.dll load: NOT OBSERVED
IIPSCheck.dll load: NOT OBSERVED
IIPSHost.dll load: NOT OBSERVED
IIPSVFS.dll load: NOT OBSERVED
```

No IIPS dependency DLLs were observed in runtime module lists.

## `0x8189FEC`

No runtime register/stack capture of `0x8189FEC` was made. No static
constant was found in EXE/Base/iips.dll. It remains:

```text
8189FEC_PACKED_OR_VM_GENERATED
```

No new evidence assigns it to `GetResourceManagerII`, HostApp, or IFS2.

## Answers

1. Who loaded `iips.dll`: caller not confirmed.
2. `iips.dll` DllMain success: not observed.
3. `GetResourceManagerII` resolved: not observed.
4. `GetResourceManagerII` called: not observed.
5. Created `iipsinit` window: not observed at callsite level.
6. Error UI caller: not confirmed.
7. Last native execution node before fatal: not isolated.
8. Last project DLL before fatal: unresolved; `iips.dll` is the last IIPS-land module in some runs.
9. IIPS dependency DLLs: none observed.
10. `8189FEC` runtime source: not found.
11. Globals involved in IIPS caller: not observed.
12. New L3/L4 execution node: no.

## Final

```text
IIPS_LOADER_CALLER_UNCONFIRMED
IIPS_INIT_CALLER_UNCONFIRMED
8189FEC_RUNTIME_SOURCE_UNCONFIRMED
NO_NEW_EXECUTION_NODE
```
