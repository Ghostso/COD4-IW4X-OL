# ICH-006 — Bidirectional Runtime Boundary Cross-Comparison

## 0. Objective & Method

Core question: Can IW4X/IW4 known Runtime structures constrain CODOL's
current UNKNOWN regions through bidirectional correspondence?

This is NOT "graft IW4X onto CODOL". It is a structural lineage check:

```text
Direction A  IW4X → CODOL   (known runtime structure → does CODOL have a match?)
Direction B  CODOL → IW4X   (known CODOL evidence → does IW4X have a match?)

Only when BOTH directions produce evidence can confidence be raised.
```

Evidence allowed: source/symbol, PE imports/exports, strings, file formats,
resource paths, function/data references, known IW4 lineage structures.

Evidence forbidden: `.tvm0` internals, ordinal-1 lifecycle re-analysis,
dynamic debugging, injection, binary modification, WeGame/TCLS expansion,
historical Bootstrap RVA re-scan.

---

## 1. Direction A: IW4X → CODOL

Starting from ICH-002-A/B frozen conclusions, each IW4X known layer is
searched for a CODOL counterpart.

### 1.1 Entry → Runtime Boundary

IW4X known chain:

```text
DllMain → hook 0x6BAC0F → Main::EntryPoint
  → __security_init_cookie
  → Initialize() (environment, components)
  → return Game::__tmainCRTStartup (0x06BAA2F)
  → Original IW4 Runtime
```

CODOL counterpart:

```text
EXE Entry 0x0E5DC690 (single FF15) → Base.dll ordinal-1 (.tvm0)
  → no return to EXE
  → no confirmed post-ordinal1 EXE code execution
```

Both have an "Entry/Bootstrap" layer. But the mechanism is completely
different: IW4X hooks and returns; CODOL calls a non-returning VM stub.

The IW4X `__tmainCRTStartup` (0x06BAA2F) is a directly addressable,
source-confirmed, callable CRT entry. CODOL has no equivalent addressable
pre-runtime callable — the only structural candidate (EXE Entry) delegates
to VM and never returns.

```text
IW4X_TO_CODOL = PARTIAL
  (structural layer exists: "Entry/Bootstrap"; mechanism differs)

CODOL_TO_IW4X = CONFIRMED
  (CODOL EXE Entry is a confirmed boundary; lineage to IW4 Entry/CRT
   concept exists but mechanism differs)
```

### 1.2 CRT / Startup Environment

IW4X known:

```text
__security_init_cookie (0x06CA062) before any exception handling
SetProcessDEPPolicy, SetCurrentDirectory, SetDllDirectory
std::srand before original CRT
```

CODOL counterpart:

```text
Base.dll internal CRT/locale init exists post-ordinal1
Crashes at Base+0x306A (this=3)
EXE side: no pre-entry CRT init found
TLS directory present but callbacks virtual-only
```

The CRT layer exists in CODOL only behind the VM boundary. No EXE-side
pre-entry CRT setup is confirmed.

```text
IW4X_TO_CODOL = UNKNOWN
  (CRT init exists in Base.dll but is unreachable/broken)

CODOL_TO_IW4X = PARTIAL
  (CRT concept exists; specific IW4X functions have no CODOL match)
```

### 1.3 Command Line

IW4X known:

```text
Flags::ParseFlags() in-place strips quotes from GetCommandLineA/W buffer
Flags::HasFlag() lazy init during Component construction
```

CODOL counterpart:

```text
argv count global  0x0196928C  (write site 0x00561119)
argv array global  0x01969290  (write site 0x0056111E)
provider slot      0x00CA827C  (call site 0x00561133)
gate predicate     0x37F580    (scans -q/-qa)
gate byte          0x0849413B  (write site 0x00239C68)
-src=tgp gate      0x0849B501
```

All confirmed as EXE-owned static structures. But they execute post-boundary.

```text
IW4X_TO_CODOL = PARTIAL
  (command-line parsing exists at same conceptual layer; different
   implementation: in-place buffer modification vs argv globals+gate byte)

CODOL_TO_IW4X = CONFIRMED
  (CODOL structures are confirmed; they map to IW4X's command-line
   parsing concept at the same "startup context" layer)
```

### 1.4 Filesystem

IW4X known (ICH-002-B):

```text
FS_FOpenFileRead, FS_Read, FS_FCloseFile, FS_ListFiles, FS_Restart
FS_AddLocalizedGameDirectory, Sys_DefaultInstallPath
fs_homepath/fs_cwd/fs_basepath dvar hooks
basePath validity check removal, file count expansion
```

CODOL counterpart search results:

```text
EXE strings:  main\%s, main\video, settings_c.zip.iw4, settings_m.zip.iw4,
              players/config_mp.cfg, fastfile, zone, pak, localization
Code refs:    main\%s (1 at 0x00239B7C), settings_c.zip.iw4 (1 at 0x00054C4F)
              all others: 0 code refs
Confirmed FS init/open/read chain: NONE (exe_filesystem_candidates.csv = UNKNOWN)
EX-015 dynamic:    no game file API before Base+0x306A crash
```

CODOL has path names but no confirmed FS loader code. The consuming code
is behind the VM/virtual-only boundary.

```text
IW4X_TO_CODOL = UNKNOWN
  (IW4 FS structure is known; CODOL counterpart not confirmed)

CODOL_TO_IW4X = UNKNOWN
  (CODOL path strings exist but do not map to IW4 FS functions)
```

### 1.5 IWD

IW4X known (ICH-002-B):

```text
FS_IsShippedIWD (0x642440), iwd_t struct, searchpath injection,
IwdFreeStub, usermap IWD registration
```

CODOL counterpart:

```text
No .iwd files on disk
settings_*.zip.iw4 magic = SEMV (not ZIP, not IWD)
No IWD reader code found
No checksum/hash/virtual-path/package-lookup confirmed
```

```text
IW4X_TO_CODOL = NO_MATCH
  (IW4 IWD layer is confirmed; CODOL has no IWD files and no reader code)

CODOL_TO_IW4X = NO_MATCH
  (CODOL settings_*.zip.iw4 use SEMV magic, not IWD format)
```

Note: NO_MATCH means the CODOL layer demonstrably does not use IW4's IWD
format or reader. This is distinct from UNKNOWN (where evidence is
insufficient to determine whether a match exists).

### 1.6 Zone Loader

IW4X known (ICH-002-B):

```text
DB_LoadXAssets (0x4E5930), DB_ReadXFile (0x445460)
FastFiles::GetZoneLocation, ReadVersionStub, ReadHeaderStub
DB_FindXAssetHeader, asset pool, XAsset types
```

CODOL counterpart:

```text
No .ff files on disk
'zone' and 'fastfile' strings exist in EXE but 0 code refs
No DB_LoadXAssets / DB_ReadXFile / DB_FindXAssetHeader found
No IWff / IW4x magic found
```

```text
IW4X_TO_CODOL = UNKNOWN
  (IW4 Zone loader is confirmed; CODOL may have one behind VM but
   cannot be confirmed from accessible evidence)

CODOL_TO_IW4X = UNKNOWN
  (CODOL has zone/fastfile strings but no confirmed loader structure)
```

### 1.7 Asset DB

IW4X known (ICH-002-B):

```text
DB_XAssetPool (0x7998A8), g_poolSize (0x7995E8)
DB_FindXAssetHeader (0x407930), DB_AddXAsset (0x5BB650)
Asset pool expansion, type callbacks
```

CODOL counterpart:

```text
No XAsset/material/image/model/sound/weapon/font/stringtable
  type strings or structures found in EXE plain text
No DB_* function bindings found
No asset pool pointer tables confirmed
```

```text
IW4X_TO_CODOL = UNKNOWN

CODOL_TO_IW4X = UNKNOWN
```

### 1.8 Game Runtime

IW4X known (ICH-002-A/B):

```text
Original IW4 Runtime: Com_Init → FS_Init → DB_Init → CL_Init
Renderer (D3D9), client game structures, main loop with
render/input/network tick
```

CODOL counterpart:

```text
exe_runtime_layer_model.csv:
  Common Engine = NO_CONFIRMED_REGION
  IW4-derived engine = NO_CONFIRMED_REGION
  Game Runtime = NO_CONFIRMED_REGION
exe_subsystems.csv:
  Renderer = UNKNOWN_SUBSYSTEM
  GameInit = UNKNOWN_SUBSYSTEM
  MainLoop = MAIN_LOOP_CANDIDATE (unconfirmed)
CODOL_RUNTIME_MODULE_ANALYSIS.md:
  GAME_RUNTIME_MODULE = UNKNOWN
```

The EXE exports 22 Scaleform C++ symbols (mangled names), proving a
Scaleform/UI subsystem linkage exists in the CODOL binary. These are
confirmed code addresses in the `.tp3` executable section. However, they
are UI-layer, not core game runtime.

```text
IW4X_TO_CODOL = UNKNOWN
  (IW4 Runtime structure is known; CODOL Game Runtime not confirmed
   in accessible code. Scaleform exports provide a UI-layer anchor
   but not a core game runtime match.)

CODOL_TO_IW4X = PARTIAL
  (CODOL Scaleform exports exist as confirmed addresses; IW4X also
   uses Scaleform/GFx for UI. This is a shared technology-layer
   correspondence, not a core engine runtime match.)
```

### 1.9 Platform Glue

IW4X known:

```text
CEG bypass, Auth bypass, QuickPatch, FS hooks, zone path injection
```

CODOL counterpart:

```text
TenProxy.dll Invoke(0x566) → CTclsProxy — confirmed Base.dll dynamic
  import descriptor at Base+0x88FA7C-0x88FA98
TCLS shared-memory TCLS_SHAREDMEMEMORY<PID> — confirmed producer/
  consumer pair (ex067)
IIPS/IFS2 platform boundary — confirmed (EX-047~060)
Base.dll has LoadLibraryA/GetProcAddress for dynamic resolution
```

CODOL has a complete, confirmed platform glue layer (TenProxy/TCLS/IIPS).
IW4X replaced its platform glue (CEG/Steam) with its own. The two are
different platform layers serving the same role.

```text
IW4X_TO_CODOL = PARTIAL
  (both have platform glue; implementations are completely different)

CODOL_TO_IW4X = CONFIRMED
  (CODOL TenProxy/TCLS/IIPS chain is confirmed; IW4X had a similar
   platform layer it replaced with its own compatibility)
```

---

## 2. Direction B: CODOL → IW4X

Starting from confirmed CODOL evidence, each item is checked against
IW4X/IW4 for structural correspondence.

### 2.1 EXE Entry

```text
CODOL: EXE Entry = single FF15 call to Base.dll ordinal-1
IW4X:  Host PE Entry → CRT __tmainCRTStartup (0x06BAA2F)

Correspondence: STRUCTURAL MATCH (both are "first executable action")
Mechanism:      NO_MATCH (CODOL delegates to VM; IW4 calls CRT)
```

### 2.2 Base.dll ordinal-1

```text
CODOL: Non-returning VM entry stub → .tvm0
IW4X:  No equivalent — IW4X hooks the entry directly, no VM intermediate

Correspondence: NO_MATCH
```

### 2.3 Gate tokens / argv structures

```text
CODOL: -q/-qa/-src=tgp strings + argv globals + gate byte + provider slot
IW4X:  Flags::ParseFlags/HasFlag + GetCommandLineA/W buffer modification

Correspondence: STRUCTURAL MATCH (both parse startup command line)
Mechanism:      PARTIAL (different implementation, same conceptual layer)
```

### 2.4 settings_*.zip.iw4

```text
CODOL: SEMV magic proprietary serialization (167/82 bytes)
IW4X:  No SEMV format known; IW4X uses IW4x zone header ('IW4x') and
       IWff/IWffu fastfile magic

Correspondence: NO_MATCH (format incompatible)
```

### 2.5 main/*.bk2, main/*.demo

```text
CODOL: Bink2 video files (.bk2) and game demo recordings (.demo)
IW4X:  IW4 uses .bik (Bink1) and .dm_* (demo files); .bk2 is Bink2,
       a newer codec. File format differs from IW4 lineage.

Correspondence: PARTIAL (both use Bink family for video; codec version
                differs: IW4=Bink1, CODOL=Bink2)
```

### 2.6 players/config_mp.cfg

```text
CODOL: config_mp.cfg exists on disk
IW4X:  IW4 uses config_mp.cfg (same filename, same purpose)

Correspondence: CONFIRMED (same filename, same role, IW4 lineage)
```

### 2.7 Scaleform exports

```text
CODOL: 22 confirmed Scaleform C++ mangled exports in EXE
IW4X:  IW4 uses Scaleform/GFx for UI rendering

Correspondence: CONFIRMED (shared Scaleform technology, confirmed by
                mangled symbol names in both)
```

### 2.8 TenProxy / TCLS / IIPS

```text
CODOL: Confirmed platform glue (TenProxy Invoke, TCLS shared memory,
       IIPS/IFS2 network file-stream)
IW4X:  No Tencent platform components; IW4X replaces platform with
       its own CEG/Auth bypass

Correspondence: PARTIAL (both have a "platform glue" layer serving
                the same role; implementations are incompatible)
```

### 2.9 Network/STUN candidate

```text
CODOL: 0x6212C0 network/STUN mode selection, reads gate bytes,
       selects stun1-tub.codol.qq.com vs stun.us.demonware.net
IW4X:  IW4X has network init but does not use STUN mode selection
       in the same way; Demonware endpoints are IW4-era

Correspondence: PARTIAL (Demonware endpoint in CODOL suggests IW4
                lineage; CODOL-specific endpoint suggests fork)
```

---

## 3. Bidirectional Matrix

| Layer | IW4X Evidence | CODOL Evidence | IW4X→CODOL | CODOL→IW4X | Confidence |
|-------|--------------|----------------|------------|------------|------------|
| Entry/Bootstrap | Source-confirmed hook+delegate | EXE→Base VM (non-returning) | PARTIAL | CONFIRMED | HIGH |
| CRT/Startup | Source-confirmed pre-CRT init | VM-side unknown; broken at Base+0x306A | UNKNOWN | PARTIAL | MEDIUM |
| Command Line | Source-confirmed buffer modification | Static globals+gate+predicate confirmed | PARTIAL | CONFIRMED | HIGH |
| Filesystem | Source-confirmed FS chain | Path strings only; no confirmed loader | UNKNOWN | UNKNOWN | LOW |
| IWD | Source-confirmed IWD reader | No IWD files; SEMV format | NO_MATCH | NO_MATCH | HIGH |
| Zone | Source-confirmed Zone loader | Strings only; 0 code refs | UNKNOWN | UNKNOWN | LOW |
| Asset DB | Source-confirmed XAsset pool | No XAsset structures found | UNKNOWN | UNKNOWN | LOW |
| Game Runtime | Source-confirmed Com_Init→MainLoop chain | NO_CONFIRMED_REGION; Scaleform exports exist | UNKNOWN | PARTIAL | LOW |
| Platform Glue | IW4X replaces CEG/Auth/Steam | TenProxy/TCLS/IIPS confirmed | PARTIAL | CONFIRMED | HIGH |

Note: NO_MATCH is used only for IWD (both directions agree: CODOL does
not use IW4's IWD format). All other layers are UNKNOWN because the
CODOL-side evidence is behind VM/virtual-only boundary.

---

## 4. Three Final Judgments

### 4.1 LINEAGE_CORRESPONDENCE

```text
LINEAGE_CORRESPONDENCE = PARTIAL
```

Evidence supporting correspondence:

```text
1. CODOL EXE PDB path contains "iw4\game\pc\"
2. Scaleform C++ mangled exports (22 confirmed addresses)
3. players/config_mp.cfg (same filename/purpose as IW4)
4. Demonware STUN endpoint string (IW4-era platform)
5. .bk2 (Bink2) video codec (Bink family, newer generation)
6. Command-line gate concept (same startup layer)
```

Evidence against / limiting:

```text
1. .tvm0 VM boundary has no IW4 counterpart
2. settings_*.zip.iw4 SEMV format is not IW4 IWD/Zone
3. No IW4-typical FS/DB functions or structures confirmed
4. No Game Runtime cluster confirmed
5. Bootstrap mechanism completely different
```

The lineage is real (PDB path is the strongest single evidence) but the
executable code implementing it is behind a VM boundary that prevents
structural confirmation.

### 4.2 RUNTIME_BOUNDARY_CORRESPONDENCE

```text
RUNTIME_BOUNDARY_CORRESPONDENCE = UNKNOWN
```

The key question is: Can IW4X's known Runtime boundary (CRT →
Com_Init → FS_Init → DB_Init → CL_Init) be projected onto CODOL's
observable boundaries?

Answer: NO.

```text
IW4X boundary chain (all addressable):
  __tmainCRTStartup (0x06BAA2F) → runtime functions → engine main

CODOL boundary chain (only first step addressable):
  EXE Entry (0x0E5DC690) → Base ordinal-1 (.tvm0) → ??? → UNKNOWN
```

The single confirmed CODOL boundary (EXE Entry → Base ordinal-1) does
not correspond to any IW4X runtime boundary. IW4X has no VM intermediate.
Everything after ordinal-1 in CODOL is UNKNOWN.

Therefore: the current static evidence cannot project IW4X Runtime
structure onto CODOL's VM/virtual-only regions.

### 4.3 RESTORATION_TARGET_IDENTIFIABILITY

```text
RESTORATION_TARGET_IDENTIFIABILITY = UNKNOWN
```

To identify a restoration target, we need at least one confirmed CODOL
address that serves as a "runtime entry" — the analog of IW4X's
`__tmainCRTStartup` (0x06BAA2F).

Current state:

```text
Candidate:  EXE Entry (0x0E5DC690) — but this delegates to VM, never returns
Candidate:  0x77F580 (gate head) — but virtual-only, not dynamically observed
Candidate:  Scaleform exports — but UI-layer, not core game runtime
Candidate:  TenProxy Invoke — but platform glue, not game runtime

None satisfies the minimum requirement:
  "confirmed address + executable + game-runtime semantics +
   reachable without touching .tvm0/ordinal-1"
```

No restoration target can be identified from current static evidence.

---

## 5. Key Question Answer

> **Can IW4X provide "structural reference" for CODOL, even if it cannot
> provide directly reusable Runtime?**

```text
ANSWER = PARTIAL
```

What IW4X CAN provide:

```text
1. Lineage confirmation (PDB path "iw4\game\pc\" is definitive)
2. Conceptual layer mapping (Entry/Bootstrap, CRT/Env, CmdLine,
   FS, Zone, AssetDB, GameInit, MainLoop — the layer names are valid)
3. Scaleform/UI technology correspondence (confirmed by exports)
4. Platform glue role mapping (TenProxy = what IW4X replaced CEG with)
5. File format hints (.bk2 = Bink2, config_mp.cfg = shared convention)
```

What IW4X CANNOT provide:

```text
1. Address-level function mapping (no CODOL address maps to any
   IW4X function except Scaleform exports)
2. FS/IWD/Zone/AssetDB structural equivalence (CODOL uses different
   formats or the code is inaccessible)
3. Bootstrap delegation target (CODOL ordinal-1 never returns;
   IW4X's hook-and-return pattern does not apply)
4. Game Runtime entry identification (no confirmed CODOL runtime
   entry point exists)
```

---

## 6. Convergence Point Assessment

The critical question for ICH-006: Has a structural correspondence
convergence point been found?

```text
IW4X known Runtime boundary
          │
          │ structural correspondence
          ↓
CODOL observable boundary
          │
          └──→ can define next-stage experiment target?
```

```text
CONVERGENCE_POINT_FOUND = NO
```

The only confirmed convergence is at the **technology lineage** level
(PDB path, Scaleform, config_mp.cfg, Bink codec family), not at the
**functional boundary** level (no CODOL address corresponds to any
IW4X runtime function).

This means:

```text
当前静态证据无法把 IW4X Runtime 结构投影到
CODOL 的 VM/virtual-only 区域。
```

This is a definitive research conclusion, not a failure. It establishes
that the current evidence methodology (static analysis of file-backed
PE sections) has reached its ceiling for CODOL's VM-protected binary.

---

## 7. NEXT_RESEARCH_DIRECTION

```text
ICH006_STATUS = COMPLETE

NEXT_RESEARCH_DIRECTION =
  Current static evidence system cannot cross CODOL's
  VM/virtual-only boundary. The bottleneck is no longer
  "which DLL to analyze" or "which string to search".

  The bottleneck is structural: the CODOL EXE delegates all
  runtime initialization to a VM-protected region (.tvm0 /
  virtual-only .tp3) that cannot be analyzed without either:
    (a) dynamic instrumentation to observe runtime code
        materialization/execution inside the VM boundary
    (b) VM bytecode recovery/decoding (requires .tvm0
        analysis, currently prohibited by task scope)
    (c) an entirely new evidence source (e.g., debug symbols,
        leaked source, server binary, or a different build)

  Recommend: Decision point — authorize one of (a)/(b)/(c)
  or accept that static-only analysis has reached its limit.
```

---

## 8. Artifacts

```text
ICH006_BIDIRECTIONAL_RUNTIME_COMPARISON.md      (this file)
ICH006_BIDIRECTIONAL_RUNTIME_MATRIX.csv         (9 rows)
```

## 9. Compliance

| Constraint | Status |
|------------|--------|
| No CODOL launch | PASS |
| No IW4X launch | PASS |
| No dynamic debugging | PASS |
| No injection | PASS |
| No binary modification | PASS |
| No .tvm0 analysis | PASS |
| No ordinal-1 lifecycle re-analysis | PASS |
| No WeGame/TCLS expansion | PASS (frozen EX-067/068 cited only) |
| No historical Bootstrap RVA re-scan | PASS (frozen CORE-011/012 cited only) |
| Bidirectional evidence required | PASS |
| NO_MATCH vs UNKNOWN distinguished | PASS |
| No auto ICH-007 | PASS |

---

*ICH-006 完成。停止。*
