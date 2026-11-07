# CODOL_RUNTIME_MODULE_ANALYSIS

## Scope

```text
ANALYSIS = MODULE_INVENTORY_AND_RUNTIME_OWNERSHIP
PROCESS_LAUNCHED = NO
BINARY_MODIFIED = NO
MODULES_INVENTORIED = 44
```

## Findings

The module inventory covers the native PE files under `COD OL`. No second standalone game executable was found. The largest native module is `codoMP_client_shipRetailBase.dll`, but its role remains `UNKNOWN` until ordinal-1 behavior is resolved.

## Top Module Candidates

| Module | Score | Engine | Network | Renderer | FS | CODOL | Confidence |
|---|---:|---:|---:|---:|---:|---:|---|
| TerSafe.dll | 62 | 14 | 65 | 6 | 5 | 10 | PLATFORM |
| BugTrace.dll | 51 | 5 | 39 | 3 | 5 | 6 | PLATFORM |
| TenRpcs.dll | 49 | 4 | 4 | 6 | 3 | 1 | PLATFORM |
| libGLESv2.dll | 48 | 132 | 5 | 307 | 0 | 4 | UTILITY |
| GCloudVoice.dll | 47 | 80 | 99 | 3 | 2 | 5 | UTILITY |
| TP3Helper.exe | 37 | 1 | 11 | 7 | 1 | 5 | CANDIDATE |
| GameRpcs.dll | 36 | 2 | 0 | 9 | 1 | 6 | CANDIDATE |
| GbSpy.dll | 34 | 1 | 5 | 23 | 1 | 3 | UNKNOWN |
| ACE-DRV32.dll | 30 | 3 | 3 | 2 | 1 | 1 | PLATFORM |
| TCJ.dll | 30 | 1 | 7 | 3 | 1 | 5 | PLATFORM |
| PolicyProbe.dll | 29 | 1 | 11 | 2 | 1 | 5 | PLATFORM |
| TenSLX.dll | 29 | 1 | 1 | 4 | 1 | 5 | PLATFORM |
| codoMP_client_shipRetailBase.dll | 28 | 0 | 0 | 0 | 0 | 4 | UNKNOWN |
| codoMP_client_shipRetailBase.dll | 28 | 0 | 0 | 0 | 0 | 4 | UNKNOWN |
| codoMP_client_shipRetailBase.dll | 28 | 0 | 0 | 0 | 0 | 4 | UNKNOWN |

## Ownership Decision

```text
GAME_RUNTIME_MODULE = UNKNOWN
ENGINE_RUNTIME_MODULE = UNKNOWN
PLATFORM_RUNTIME_MODULE = CANDIDATE: codoMP_client_shipRetailBase.dll
CODE_BASE = NO_CONFIRMED_RUNTIME_MODULE
```

The previous EXE analysis established that the EXE does not contain a confirmed IW4/CODOL runtime. This pass does not promote any DLL on size or filename alone. `codoMP_client_shipRetailBase.dll` is the only module with a confirmed inbound boundary from the EXE, but its ordinal-1 role remains unresolved and it is not classified as the game runtime.

The highest-scoring native modules are dominated by anti-cheat, telemetry, RPC, audio/video, graphics-wrapper, and Tencent platform components. None has a demonstrated combined cluster of engine initialization, renderer, filesystem, Dvar/console, script, and game-interface evidence.

## Answers

1. **Game runtime in EXE?** No confirmed EXE runtime module.
2. **If not in EXE, which DLL?** `UNKNOWN`; `codoMP_client_shipRetailBase.dll` is the only confirmed external boundary, not a confirmed runtime owner.
3. **Most IW4/COD6-like DLL?** `NO_CONFIRMED_RUNTIME_MODULE`.
4. **Most CODOL-like runtime DLL?** `NO_CONFIRMED_RUNTIME_MODULE`.
5. **Renderer location?** `UNKNOWN`; renderer strings alone are insufficient.
6. **Filesystem/asset system?** `UNKNOWN`; no address-level runtime cluster found.
7. **Dvar/command system?** `UNKNOWN`; no address-level runtime cluster found.
8. **Network runtime?** `UNKNOWN`; EXE-side STUN evidence remains a candidate only.
9. **Does Base ordinal 1 load/transfer to runtime?** `UNKNOWN`; only the EXE->ordinal-1 boundary is confirmed.
10. **Best prototype base?** `NO_CONFIRMED_RUNTIME_MODULE`; do not select a DLL without a confirmed runtime entry cluster.

## Stop Condition

This is a valid `NO_CONFIRMED_RUNTIME_MODULE` result. No forced winner is selected and no new CORE series is created.
