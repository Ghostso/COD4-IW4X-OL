# ICH-005 — CODOL Runtime/Data Reachability

## 0. Scope & Fixed Inputs

Core question: Does the CODOL original FS → IWD → Zone → Asset → Game Runtime
chain still exist? If so, which parts can serve as a restoration basis without
touching `.tvm0`/ordinal-1?

```text
CODOL EXE          = codoMP_client_shipRetail.exe (SHA256 frozen)
Known deps         = IIPS/IFS2, Base.dll, TenProxy.dll
Local assets       = main/*.bk2, main/*.demo, players/config_mp.cfg,
                     players/settings_*.zip.iw4
IW4X reference     = ICH-002-B frozen conclusions (Original FS/IWD/Zone/AssetDB)
Constraint         = No .tvm0 analysis, no ordinal-1 re-analysis,
                     no dynamic debugging, no binary modification
```

---

## 1. Filesystem (Layer 01)

### 1.1 On-disk data layout

```text
COD OL\main\video\*.bk2        49 files  (783 MB, Bink2 video)
COD OL\main\demo\*.demo       31 files  ( 80 MB, game demo recordings)
COD OL\players\config_mp.cfg    1 file  (7.8 KB, game config)
COD OL\players\settings_c.zip.iw4  167 bytes  (NOT zip: magic SEMV)
COD OL\players\settings_m.zip.iw4   82 bytes  (NOT zip: magic SEMV)
```

No `.iwd`, `.ff`, or standard IW4 zone files exist on disk.

### 1.2 EXE-side FS evidence

| Evidence | RVA | Code refs | Status |
|----------|-----|-----------|--------|
| `main\%s` string | 0x009DBF24 | 1 (0x00239B7C) | CANDIDATE |
| `main\video` string | 0x009C0A33 | 0 | CANDIDATE |
| `settings_c.zip.iw4` string | 0x009B51F8 | 1 (0x00054C4F) | CANDIDATE |
| `settings_m.zip.iw4` string | 0x009B520C | 0 | CANDIDATE |
| `players/config_mp.cfg` string | 0x009BCFE0 | 0 | CANDIDATE |
| `fastfile` string | cluster | 0 | UNKNOWN |
| `zone` string | cluster | 0 | UNKNOWN |
| `pak` string | cluster | 0 | UNKNOWN |

Source: `exe_core007_resource_refs.csv`; `exe_strings_clusters.csv`

### 1.3 Confirmed FS init/open/read chain

```text
exe_filesystem_candidates.csv : UNKNOWN
  "no confirmed EXE-native resource/filesystem init chain recovered"

exe_subsystems.csv FileSystem    : UNKNOWN_SUBSYSTEM
  "no confirmed open/read/fastfile chain in EXE plain text"

EX-015 dynamic trace             : NO game file API before Base+0x306A crash
  "CreateFileA hit only ntdll.dll; no CreateFileW/FindFirstFile game-path hits"
```

### 1.4 IIPS/IFS2 classification

IIPS/IFS2 is NOT a game resource layer:

```text
IFS2.dll is loaded by iips.dll CNIFS::initIfsLib (EX-051/052 static L2)
IFS2 provides network file-stream / QoS infrastructure, not game data reads
IFS2 init occurs post-gate, before the first game file access (EX-015)
IIPS boundary blocks progression past WIN_IIPS_INIT_ERROR (8189FEC)
```

### 1.5 Verdict

```text
CODOL_FILESYSTEM = UNKNOWN
```

EXE contains path references proving the design target, but no confirmed
filesystem initialization, open, read, or search-path chain exists in
plain-text code. Data layout exists on disk but has no confirmed consumer.

---

## 2. IWD / ZIP (Layer 02)

### 2.1 File format reality

```text
settings_*.zip.iw4 magic bytes:
  53 45 4D 56 03 00 00 00 ...
  = "SEMV" + version 3
  NOT PK\x03\x04 (standard ZIP local file header)
```

The `.zip.iw4` extension is misleading. These are proprietary serialization
blobs, not ZIP archives, not IWD archives, not IW4 fastfiles.

### 2.2 IWD traces

```text
No .iwd files on disk                      = 0
No IWD reader code found in EXE            = NOT_FOUND
No IW4 FS_IsShippedIWD / iwd_t equivalent  = NOT_FOUND
No checksum/hash/virtual-path/lookup       = NOT_FOUND
```

### 2.3 Verdict

```text
CODOL_IWD = UNKNOWN
```

No native IWD reader or IW4 lineage archive format recognition was found
in the CODOL EXE. `settings_*.zip.iw4` files use a proprietary SEMV magic
that does not map to IW4's IWD or Zone format.

---

## 3. Zone Loader (Layer 03)

### 3.1 Static evidence search results

| Search term | Hits in EXE | Code refs | Confirmed loader |
|-------------|-------------|-----------|-----------------|
| `zone` | string cluster only | 0 | NO |
| `fastfile` | string cluster only | 0 | NO |
| `.ff` files on disk | 0 | — | — |
| `loadzone` | 0 | 0 | NO |
| `zoneload` | 0 | 0 | NO |
| `asset pool` | 0 | 0 | NO |
| `DB_*` | 0 | 0 | NO |
| `IWff` magic | 0 | 0 | NO |
| `IW4x` magic | 0 | 0 | NO |

### 3.2 `.tvm0` / ordinal-1 exclusion

Per constraint, `.tvm0` and ordinal-1 internals were not analyzed. If a
Zone loader exists in CODOL, it may reside inside the VM boundary or in
virtual-only code space, neither of which is accessible through current
static analysis.

### 3.3 Verdict

```text
CODOL_ZONE_LOADER = UNKNOWN
```

No confirmed Zone loader exists in EXE plain-text. `zone`/`fastfile` strings
exist but have 0 code references. No `.ff` files exist on disk. The zone
loading mechanism may exist behind the VM boundary but cannot be confirmed
without violating the task constraint.

---

## 4. Asset DB (Layer 04)

### 4.1 IW4-typical asset type search

| Asset type keyword | Hits in EXE strings | Code refs | Status |
|--------------------|--------------------|-----------|--------|
| XAsset | 0 | 0 | NOT_FOUND |
| asset pool | 0 | 0 | NOT_FOUND |
| material | 0 | 0 | NOT_FOUND |
| image | 0 | 0 | NOT_FOUND |
| model | 0 | 0 | NOT_FOUND |
| sound | 0 | 0 | NOT_FOUND |
| weapon | 0 | 0 | NOT_FOUND |
| font | string only | 0 | UNKNOWN |
| stringtable | 0 | 0 | NOT_FOUND |
| localization | string only | 0 | UNKNOWN |
| DB_FindXAssetHeader | 0 | 0 | NOT_FOUND |
| DB_XAssetPool | 0 | 0 | NOT_FOUND |
| DB_LoadXAssets | 0 | 0 | NOT_FOUND |

### 4.2 Verdict

```text
CODOL_ASSET_DB = UNKNOWN
```

No IW4-typical asset database structures, type enumerations, pool pointers,
or lookup functions were found in the CODOL EXE plain-text. The asset system
may exist behind the VM boundary or in virtual-only code, but cannot be
confirmed from available evidence.

---

## 5. Game Runtime (Layer 05)

### 5.1 Subsystem status (from frozen CSV evidence)

| Subsystem | exe_subsystems.csv status | evidence |
|-----------|--------------------------|----------|
| Bootstrap | CANDIDATE | Entry→Base ordinal1→VM boundary observed |
| Command Line | CANDIDATE | strings present; parser unconfirmed |
| FileSystem | UNKNOWN_SUBSYSTEM | no confirmed open/read chain |
| Renderer | UNKNOWN_SUBSYSTEM | strings present; D3D/present chain unconfirmed |
| Game Init | UNKNOWN_SUBSYSTEM | no confirmed game init chain |
| Main Loop | MAIN_LOOP_CANDIDATE | no confirmed frame/render/present loop |
| Network | UNKNOWN_SUBSYSTEM | strings present; chain unconfirmed |

### 5.2 Runtime layer model (from frozen CSV evidence)

```text
Layer 4  Common Engine       = NO_CONFIRMED_REGION
Layer 5  IW4-derived engine  = NO_CONFIRMED_REGION
Layer 7  Game Runtime        = NO_CONFIRMED_REGION
```

Source: `exe_runtime_layer_model.csv`

### 5.3 Module ownership (from frozen analysis)

```text
GAME_RUNTIME_MODULE   = UNKNOWN
ENGINE_RUNTIME_MODULE = UNKNOWN
CODE_BASE             = NO_CONFIRMED_RUNTIME_MODULE
```

Source: `CODOL_RUNTIME_MODULE_ANALYSIS.md`

### 5.4 Bootstrap ≠ Game Runtime distinction

Confirmed CODOL structures:

```text
Entry stub                  = CONFIRMED (single FF15 call)
Base.dll ordinal-1 boundary = CONFIRMED (non-returning VM stub)
Gate tokens (-q/-qa/src)    = CONFIRMED (EXE-owned, plain text)
Network/STUN candidate      = CANDIDATE (0x6212C0, virtual-only)
IIPS/IFS2 boundary          = BOUNDARY (blocks progression)
```

None of these is a Game Runtime component. They are Bootstrap or Platform Glue.

### 5.5 Verdict

```text
CODOL_GAME_RUNTIME = UNKNOWN
```

No Game Runtime cluster (game logic / renderer / sound / input / network /
client structures) is confirmed to exist in any accessible CODOL PE or DLL.
The EXE runtime layer model explicitly states `Game Runtime =
NO_CONFIRMED_REGION`, and no module has been promoted to runtime owner.

---

## 6. Bootstrap (Layer 06)

```text
CODOL_BOOTSTRAP = MISSING
```

ICH-004 conclusion:

```text
BRIDGE_BOUNDARY = EXE_ENTRY (CANDIDATE only)
RUNTIME_BRIDGE_FEASIBILITY = LOW
ENVIRONMENT_SETUP = MISSING
COMPATIBILITY_LAYER = MISSING
ORIGINAL_RUNTIME_HANDOFF = MISSING
```

Source: `ICH004_BOOTSTRAP_BRIDGE.md`

---

## 7. Platform Glue (Layer 07)

```text
CODOL_PLATFORM_GLUE = MISSING
```

No compatibility initialization layer exists in the CODOL EXE. The EXE
Entry is a single call to a non-returning VM stub. There is no hook point
before the VM boundary where compatibility patches could be installed.

Source: `ICH004_BOOTSTRAP_BRIDGE.md` (COMPATIBILITY_INITIALIZATION = MISSING)

---

## 8. Cross-Analysis: CODOL vs IW4X

```text
CODOL                    IW4X
────────────────────────────────────────────────────
Filesystem      ←→      Original FS           [UNKNOWN vs CONFIRMED]
IWD             ←→      Original IWD          [UNKNOWN vs CONFIRMED]
Zone            ←→      Original Zone         [UNKNOWN vs CONFIRMED]
Asset DB        ←→      Original AssetDB      [UNKNOWN vs CONFIRMED]
Game Runtime    ←→      IW4 Runtime           [UNKNOWN vs CONFIRMED]
Bootstrap       ←→      IW4X Bootstrap        [MISSING vs CONFIRMED]
Platform Glue   ←→      IW4X compatibility    [MISSING vs CONFIRMED]
```

### Classification table

| CODOL Layer | Status | Classification | Rationale |
|-------------|--------|----------------|-----------|
| Filesystem | UNKNOWN | UNKNOWN | Path strings exist but no confirmed init/access chain |
| IWD | UNKNOWN | UNKNOWN | No IWD files on disk; no reader code found; SEMV format does not map |
| Zone Loader | UNKNOWN | UNKNOWN | `zone`/`fastfile` strings exist but 0 code refs; no `.ff` files |
| Asset DB | UNKNOWN | UNKNOWN | No XAsset/pool/type structures found in EXE plain text |
| Game Runtime | UNKNOWN | UNKNOWN | `NO_CONFIRMED_REGION` in exe_runtime_layer_model.csv |
| Bootstrap | MISSING | REPLACEMENT_REQUIRED | ICH-004: ordinal-1 non-returning; no bridge candidate |
| Platform Glue | MISSING | REPLACEMENT_REQUIRED | ICH-004: no compatibility initialization window |

"存在" ≠ "可以直接复用". None of the UNKNOWN layers can be promoted to
`ORIGINAL_PRESERVED` or `POSSIBLE_REUSE` without confirmed functional code.

---

## 9. Final Decision

```text
RUNTIME_RESTORATION_FEASIBILITY = UNKNOWN

MISSING_LAYER = Bootstrap, Platform Glue
  (ICH-004 confirmed: bridge feasibility LOW;
   ordinal-1 non-returning; no delegate target)

REPLACEABLE_LAYER = UNKNOWN
  (cannot determine which layers are replaceable until
   FS/IWD/Zone/Asset/GameRuntime layers are confirmed
   to exist as functional code, not just strings/data)

ORIGINAL_LAYER_PRESERVATION = UNKNOWN
  (cannot confirm FS/IWD/Zone/AssetDB/GameRuntime as
   original preserved layers; all are UNKNOWN because
   the consuming code is behind VM/virtual-only boundary)

MINIMAL_REPLACEMENT_BOUNDARY = UNDEFINED
  (no confirmed runtime entry point exists to define
   a replacement boundary against; cannot design a
   "minimal compatible replacement layer" without a
   target to replace into)
```

### Why UNKNOWN, not LOW or PROMISING

```text
LOW would mean we have evidence that the chain does NOT exist.
PROMISING would mean we have evidence that the chain DOES exist and
  is partially reachable.

Neither is proven. The chain may exist entirely behind the VM boundary
(.tvm0 / virtual-only .tp3 sections). Current static analysis cannot
penetrate those regions. The on-disk data proves the game was designed
to use these resources, but no confirmed consumer code exists in
accessible plain-text.

The honest answer is UNKNOWN.
```

### What would be needed to upgrade

```text
To upgrade to PROMISING:
  1. Confirm at least one of FS/IWD/Zone/Asset/Game Runtime
     exists as functional code in an accessible region
  2. Or: cross the VM boundary to recover post-ordinal-1
     execution flow (requires new constraint authorization)

To upgrade to LOW:
  1. Prove that no FS/Zone/Asset/Game Runtime code exists
     anywhere in the CODOL binary (requires full VM decode)
```

---

## 10. Problem Framing Shift

ICH-004 answered the bootstrap question. ICH-005 answers the runtime/data
reachability question. Together they establish:

```text
Bootstrap  = MISSING (bridge feasibility LOW)
Runtime    = UNKNOWN (no confirmed functional layer)
Data       = EXISTS (on-disk assets confirmed but format non-standard)
Code       = UNKNOWN (VM/virtual-only boundary blocks access)
```

The problem cannot yet be formally shifted to:

```text
原始 CODOL Runtime/Data
         ↑
最小兼容/启动替代层
         ↑
本地启动环境
```

Because there is no confirmed original CODOL Runtime to build an
alternative layer toward. The shift can only occur after at least one
Runtime/Data layer is confirmed as functionally accessible.

---

## 11. Artifacts

```text
ICH005_CODOL_RUNTIME_DATA_REACHABILITY.md   (this file)
ICH005_RUNTIME_DATA_MATRIX.csv              (7 rows)
```

## 12. Compliance

| Constraint | Status |
|------------|--------|
| No .tvm0 analysis | PASS |
| No ordinal-1 re-analysis | PASS (Plan A CLOSED cited only) |
| No dynamic debugging | PASS |
| No CODOL launch | PASS |
| No IW4X launch | PASS |
| No binary modification | PASS |
| Only static evidence | PASS |
| Only ICH-002-B IW4X conclusions used | PASS |
| No "exists = reusable" conflation | PASS |
| No auto ICH-006 | PASS |

---

*ICH-005 完成。不进入 ICH-006。*
