# CODOL SECOND BOOT FINAL

Research question:

```text
Does codoMP_client_shipRetail.exe / Base.dll natively contain a second boot path
that does not depend on TCLS / Tencent platform / official launcher context?
```

## 1. Executive Summary

Based on the available static artifacts and recorded dynamic experiments in this workspace, the client does not expose a recovered native second boot path that bypasses the launcher gate. There is no plain second PE entry, no recovered TLS callback, no dynamic hit proving a command-line-driven alternate bootstrap function, and no recovered success branch around the Launcher-Required check.

The raw strings and TenProxy logs prove that Base.dll opens `TCLS_SHAREDMEMEMORY+<GamePID>` and maps it through `OpenFileMappingW` / `MapViewOfFile` before reading `GetGameSignatrue` and `GetJumpSignatrue`. The current client fails before reaching Engine/Game initialization, because Base bootstrap crashes in the CRT/locale path before returning to EXE. That failure is prior to, or concurrent with, the launcher-context requirement; it is not solved by creating a zeroed mapping.

## 2. EXE Entry / TLS

### Entry

Known chain, already confirmed:

```text
EXE Entry: 0xE5DC690
  -> call [0x0E9DC665]
  -> Base ordinal_1
  -> Base+0x149C
  -> jmp Base+0x1AA13B0 (VM boundary)
```

No second Entry or alternate CRT/WinMain entry was recovered:

- Plain export directory in EXE is non-standard / empty in normal scans.
- EXE entry calls directly into Base ordinal 1.
- Dynamic EX-021/EX-022 logs recorded no clean return before fatal path.

### TLS

EXE TLS directory:

```text
StartAddressOfRawData: 0xE9C8000
EndAddressOfRawData:   0xE9C8030
AddressOfCallBacks:    0xCADA3C
Recovered callbacks:   0
```

Base has a `.tls` section, but pefile recovery found no callback list. No TLS callback was hit in EX-021 module boot logs. This does not prove hidden TLS is impossible, but the dynamic evidence is absent, so TLS cannot be called a second boot path.

## 3. Command Line Analysis

### Game-side tokens

Base `.rdata` around `0x1088FFFC` contains:

```text
-q
-q:
id=
key=
ID=
```

These are launcher credential tokens, not game-mode flags.

Existing startup dump for `WeGame\tgp_daemon.exe` shows `GetCommandLineW`, `CommandLineToArgvW`, `StartFor`, `game_id`, `cmd_launcher_info.ini`, `-i`, `-u`, `-s`, `-f`.

### Verdict

No dynamic hit proves that `codoMP_client_shipRetail.exe` parses `-dev`, `-developer`, `-debug`, `-test`, `-local`, `-offline`, `-nosplash`, `-safe`, `-dedicated`, or `-server` into a secondary control flow. The command-line parsing evidence belongs to the WeGame/TCLS shells, not to the game client bootstrap.

## 4. "Launcher Required" Control Flow

Static string inventory:

```text
Base.dll:
  TCLS_SHAREDMEMEMORY        VA 0x1088FFFC
  TCLS_TASMEMORY_            VA 0x1089015C
  tcls_core.exe              VA 0x1088FB44
  TP3GameGuardShareMapping   VA 0x1088FAFC
  TPUSERACCOUNT_SHAREDMEMEMORY VA 0x108908D0
  TenProxy                   VA 0x1088FA88

EXE:
  WIN_NO_TCLS                VA 0x00DDBF80
  IsTCLSLogOn                VA 0x00DDD298 / 0x00E763EB
  TenProxy                   VA 0x00DC6EDC
```

Historic TenproxyLog evidence:

```text
OpenFileMapping TCLS_SHAREDMEMEMORY+<PID> Success!
MapViewOfFile Success!
GetGameSignatrue Success!
GetJumpSignatrue Success!
Post TCLS_TENPROXY_RESULT Message Success!
```

Direct xref scan result:

- Raw pointer xrefs to Base `TCLS_SHAREDMEMEMORY`: `0`.
- Raw pointer xrefs to EXE `WIN_NO_TCLS`: `0`.
- Raw pointer xref to EXE `TenProxy` exists at raw offset `0x00184F5F`.

Why the scans are clean:

- EXE is packed into `.tp3` + `.tvm0` sections; normal static slice scan cannot see the VM-decoded consumer.
- Base also contains `.tvm0`; plain section disassembly does not reveal the code that references the string cluster.
- Existing ex022 notes that breakpoints on the mapping APIs could not be installed cleanly, and no traced run observed clean return from Base to EXE.

The gate is best described as:

```text
Base/bootstrap checks named kernel objects/shared memory
  -> if fail: local WIN_NO_TCLS message path
  -> if success: TenProxy reads game/jump signatures
```

No recovered `failure -> alternative success` path exists in this data.

## 5. Engine Initialization Entry Survey

Existing EX-013/EX-014 reports map engine bootstrap references to IW4-style systems, but the project rule forbids mapping IW4X addresses into CODOL. In this workspace:

- No clean `FS_Init`, `Com_Init`, `CL_Init`, `SV_Init`, `Renderer_Init`, `DB_Init`, `Sys_Init` entry was dynamically hit.
- The earliest observable domain activity is Base CRT/locale init (`Base+0x292800`, `Base+0x288A05`, `Base+0x2F0D`) and then Base/VM boundary or crash thread activity.
- EX-013/EX-014 explicitly stop mapping IW4X addresses into CODOL.
- `libcef.dll` loads, but that is CEF startup, not Engine/Game init.

No recovered path from Base bootstrap directly into Engine initialization exists.

## 6. Dynamic Experiment Log

The following are already-recorded dynamic probes:

- `工具/logs/exe_full_20260916-214844.log`
- `工具/logs/ex022_bootstrap_exit_20260916-220012.log`
- `工具/logs/exp021.log`
- `工具/logs/exp022.log`
- `CODOL_EX021_MODULE_BOOT_RESULT.md`
- `CODOL_EX022_BOOTSTRAP_EXIT.md`

CODOLLauncher diagnostic runs on this machine:

- Game process launched with `CREATE_SUSPENDED`.
- `codoMP_client_shipRetailBase.dll` and `libcef.dll` load after resume.
- Process later reaches `致命错误` fatal window.
- Creating `TCLS_SHAREDMEMEMORY+<PID>` before resume did not move the module set beyond Base/libcef.

No successful Engine/Game initialization was reached.

## 7. Startup State Machine

```text
BOOT-0 EXE process created
BOOT-1 EXE Entry -> Base ordinal_1
BOOT-2 Base/VM boundary
BOOT-3 Thread creation / CRT locale init
BOOT-4 Platform/TCLS check (shared-memory named objects)
BOOT-5 Engine initialization        NOT REACHED
BOOT-6 FS/resource initialization   NOT REACHED
BOOT-7 Renderer                      NOT REACHED
BOOT-8 Game                          NOT REACHED
BOOT-9 Main loop                     NOT REACHED
```

Candidate local alternative path:

```text
BOOT-2 -> BOOT-5 Engine
```

No dynamic evidence supports this path in the current build.

## 8. Candidate Second Entries and Exclusion

| Candidate | Evidence level | Result |
|---|---|---|
| Standard PE Entry | L3 static, dynamic L4 partial | Same Base chain, no successful return |
| TLS callback | L1 static only; no recovered callbacks | Excluded by absence of dynamic hit |
| CRT/WinMain | L1/L2 partial | Not reached; entry goes to Base ordinal 1 |
| Command-line dev/debug mode | L1 strings only | No dynamic path found |
| Custom export ordinal 1 | L4 confirmed | Startup chain, not an alternate path |
| TenProxy Invoke | L3 partial | Blocked before Base returns |
| IW4X engine bootstrap | Static reference only | Not CODOL evidence, prohibited as direct map |

## 9. Final Result

```text
RESULT-B
```

The currently available client does not contain a discovered native second boot path that bypasses TCLS/WeGame/launcher context to start Engine/Game. This is not merely "not found": the available evidence covers:

- Entry enumeration
- TLS enumeration
- Command-line token inventory
- Launcher-Required string inventory and xref attempts
- Existing dynamic Base bootstrap logs
- Module boot logs

## 10. Evidence Matrix

| Evidence | Level | Outcome |
|---|---|---|
| EXE Entry -> Base ordinal_1 -> VM boundary | L4 | Confirmed |
| Base/libcef load in launcher test | L3 | Confirmed |
| No second PE Entry recovered | L2 | No candidate |
| TLS callbacks recovered | L2 | None |
| TLS callback dynamic hit | absent | Not a candidate |
| Command-line dev/offline path | L1 strings only | Not a candidate |
| `TCLS_SHAREDMEMEMORY` string in Base | L2 static | Confirmed string, no direct code xref |
| TenProxyLog open/map/signature | L3 runtime log | External gate confirmed |
| `WIN_NO_TCLS` string in EXE | L2 static | Gate message exists |
| Direct xref to `WIN_NO_TCLS` | L1/L2 | Not recovered |
| Engine/Game init dynamic hit | absent | Not reached |

## 11. Remaining Unknowns

- Exact Base code path that consumes the TCLS string cluster, because it resides in `.tvm0`/VM-protected code.
- Exact shared-memory structure/fields written by old launcher.
- Whether Base bootstrap would complete if all launcher context fields, not just the mapping name, were correct.
- Whether hidden/unpacked TLS or alternate entry exists inside `.tvm0` at runtime, since no debugger tools are available on this machine to prove or disprove it dynamically.
