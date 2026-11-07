# CODOL CLIENT BOOTSTRAP RECOVERY REPORT

Current level:
LEVEL 2-3 (Base DLL CRT/locale init, still before TenProxy)

Process:
`codoMP_client_shipRetail.exe` (original SHA256 `36997674...2b537`), Base `codoMP_client_shipRetailBase.dll` (original SHA256 `ef75220d...bc6a20`), TenProxy `a5ee7ede...31348cb`. Original files were never modified.

Bootstrap timeline:
S0-S2: EXE create, ntdll/kernel load, Base DLL load confirmed.
S3: Base DLL CRT/locale init starts: config string parser `Base+0x292800`, then CRT `setlocale` category parser `Base+0x288A05`.
S4-S13: not reached in any run yet.

Last confirmed good state:
EX-003 reached the end of two `LC_*` locale-category parses. Both parser cleanup calls were neutralized and returned to `Base+0x288DA8` / `Base+0xB7E67`.

First unrecoverable state:
EX-003: `Base+0x2F0D` writes `[esi+18h] = 0Fh` with `esi = 3`; access violation at `0x0000001B`. This is inside the small-string/locale object init path, called from `Base+0xB7B07 -> 0xB7E67 -> 0xC28C3` chain.
The crashing frame runs on a worker thread (`esp=0x0017E170`), after many valid locale-object initializations, so the `this=3` value is a corrupted thread/locale object pointer rather than a main-thread stack issue.
EX-004: after neutralizing `Base+0x2F0D`, the next real node is `Base+0x306A`: `cmp [ecx+18h], 10h` with `ecx=3`, AV at `0x1B`. Same `this=3` source, one instruction later.

Invalid Free:
Still present in the original binary and is a symptom, not the root. Original chain is `0x404000 -> Base+0x27E3B0 -> Base+0x27E403 -> [Base+0xB022F4] (RtlFreeHeap)`. The freed pointer `0x404000` is EXE image RVA `0x4000`, and `Base+0xAC4BFC` (heap init state) is `1`, not `3`, when the free runs.

Experimental continuation:
EX-001: `Base+0x27E40C` original `ff 15 f4 22 b0 10`, modified `b8 01 00 00 00 90`.
EX-002: adds `Base+0x2928AC` original `83 27 00`, modified `90 90 90`; next failure was `InterlockedDecrement` on `BAADF00D`.
EX-003: adds `Base+0x288C0A` original `e8 44 f7 ff ff`, modified `90 90 90 90 90`; next failure was `Base+0x2F0D` with `this=3`.
EX-004: adds `Base+0x2F0D` original `c7 46 18 0f 00 00 00`, modified `90 90 90 90 90 90 90`; next failure was `Base+0x306A` with `ecx=3`.
All experiment bytes, RVAs, and SHA256 values are recorded in `工具/EXPERIMENT_002_MANIFEST.json` and `工具/EXPERIMENT_003_MANIFEST.json`.
EX-005: provenance only, no patch. `Base+0x2ED2` entry from `.tvm0` caller `Base+0x267AC6D`; `ecx` becomes `3` inside the VM-involved path before `Base+0x306A`.
EX-006: provenance only, no patch. `ESI=3` first forms at `Base+0x2EEB` as `edi = [0x141CE020+4] = 3`, then `free(3)` copies it into `ESI` via `Base+0x27E3B0`; `.tvm0` is only the caller boundary, not the producer.
EX-007: `ba w4 0x141CE024` did not fire in a fresh run; object heap address is not stable across runs. Reported `writer UNKNOWN`, `field=object+4`, `value=3`.
EX-008: dynamic TenProxy push. `EXE+0x184F5E` not hit, TenProxy not loaded, `Invoke` not hit; blocker remains Base CRT/locale init before EXE binding consumer.
EX-009: static binding audit. `EXE+0x184F5E` has no direct caller/pointer-table reference; `CA8150/CA8158` contain RVA placeholders `0xA13848/0xA1386A` into zero-filled `.tp3`, no static writer found. Verdict: VM-internal/alternate binding path, not proven current startup chain.
EX-010: LdrLoadDll trace before `Base+0x306A` shows only system/runtime DLLs; no project DLL dynamic load, no TenProxy attempt. Runtime dispatcher is behind the `.tvm0` boundary.
EX-011-P0: EXE Entry `0xE5DC690` is reached and directly calls `Base+0x1D6582C` (Base export ordinal 1); crash at `Base+0x306A` occurs inside that call. No alternative plain Game/Engine Init entry exists outside VM-protected code.
EX-015: file API trace before `Base+0x306A` found only `C:\Windows\system32\ntdll.dll` reads; no `players/main/config/settings/*.ff/*.iwd/*.bk2` access occurred before the crash.
EX-016-FAST: Base ordinal_1 did not return to EXE before the traced endpoint. `Base+0x306A` first hit with valid object `ecx=0x128A4CE8`, later with `ecx=3`.
EX-017-EXEC: actual original run first exception was `KERNEL32!IsBadReadPtr+0x5a` on a BugTrace/crash-report thread. Single EXE-entry skip (`0xE5DC690` `call` -> `mov eax,0; ret`) loaded Base/libcef then exited via `NtTerminateProcess`; no TenProxy/Engine/Game start.
EX-018-RET: actual original runs hit `Base+0x1D6582C` but no `ret` to EXE was observed; first exception again `KERNEL32!IsBadReadPtr+0x5a`.
EX-019-BOOT: VM external boundary observed: `Base+0x149C -> jmp Base+0x1AA13B0` repeatedly; BugTrace/dbghelp load; first exception `KERNEL32!IsBadReadPtr+0x5a`; no failure->normal branch found, no patch, NO NEW NODE.
EX-020-ENGINE-ENTRY: static engine-entry scan found only unreliable candidates (`0x1321A9`, `0x239B7D`, Renderer table anchors); no clean Engine entry, no patch, NO NEW ENGINE CANDIDATE.
EX-021-MODULE-BOOT: PE/TLS scan found no recovered TLS callbacks or meaningful exports; module order EXE->Base->libcef->system->BugTrace; `NtCreateThreadEx` hits not attributable; no project DLL after Base before AV, NO MODULE BOOTSTRAP CANDIDATE.

TenProxy:
NOT LOADED. No `TenProxy.dll` or `TerSafe.dll` ModLoad line appeared in EX-002/EX-003 logs.

TCLS:
NOT REACHED. The current blocker is before any TCLS/TenProxy binding.

Game initialization:
NOT REACHED.

Renderer:
NOT REACHED.

Filesystem:
NOT REACHED.

Network initialization:
NOT REACHED.

Next concrete blocker:
Base DLL CRT locale init uses an invalid locale source pointer, so `setlocale` cleanup and locale-category setup corrupt/dereference bad objects. The next fix should supply a valid `LC_*` locale string source or initialize the Base heap state before CRT locale init, then re-run EX-003 to observe the edge after `Base+0x2F0D`.

Next experiment:
EX-005: trace where `this=3` enters the small-string/locale function, or supply a valid locale source before CRT locale init; do not NOP further nodes in the same 0x2F0D chain.

CONFIRMED:
Invalid Free is in Base CRT/locale init, not VM dispatch.
`0x404000` is an EXE image pointer, not heap.
Heap init state `Base+0xAC4BFC` is `1`, not `3`.
TenProxy is not loaded before the crash.

HIGH CONFIDENCE:
The failing parser at `Base+0x288A05` is CRT `setlocale`-style LC category parsing (`LC_COLLATE`, `LC_CTYPE`, `LC_MONETARY`, `LC_NUMERIC`, `LC_TIME`).
EX-002's `BAADF00D` is a double-release signature in the same locale cleanup path.

UNKNOWN:
Why the locale source pointer becomes `0x404000`; whether TCLS normally writes this string into Base globals.
Whether TenProxy!Invoke would be reached once CRT locale init completes.

EXPERIMENTAL ONLY:
EX-001, EX-002, EX-003 results. They are control-flow continuation probes, not a claim that the original client is healthy.

服务器阶段:
NOT STARTED / READY FOR LOCAL PROTOCOL RESEARCH
