# CODOL_EXE_BINARY_DECOMPOSITION

## Status

```text
EXE = codoMP_client_shipRetail.exe
SHA256 = 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537
ANALYSIS_SCOPE = EXE_CENTRIC
PROCESS_LAUNCHED = NO
BINARY_MODIFIED = NO
STANDALONE_ENTRY = UNKNOWN
DYNAMIC_TEST_READY = NO
```

This report is produced from the original EXE and the already-frozen
CORE/EX-* evidence. The executable is treated as a complete PE/runtime
carrier, not as a search for one standalone entry.

## PE Structure

| Section | RVA | Virtual Size | Raw Size | Executable | Virtual-only | Status |
|---|---:|---:|---:|---|---|---|
| .tp3 | 0x00001000 | 0x008A689A | 0x00593000 | YES | YES | VALID |
| .tp3 | 0x008A8000 | 0x0016DA70 | 0x0016E000 | NO | NO | VALID |
| .tp3 | 0x00A16000 | 0x0DBB1CC0 | 0x00062000 | NO | YES | VALID |
| .tp3 | 0x0E5C8000 | 0x00000031 | 0x00001000 | NO | NO | VALID |
| .tp3 | 0x0E5C9000 | 0x00009228 | 0x0000A000 | NO | NO | VALID |
| .tvm0 | 0x0E5D3000 | 0x00004000 | 0x00002000 | YES | YES | VALID |
| .tp3 | 0x0E5D7000 | 0x00082000 | 0x00006000 | YES | YES | VALID |

The sample is PE32/I386 with ImageBase `0x00400000`. The executable uses
`.tp3` section names rather than conventional `.text/.rdata/.data` names.
Large executable virtual ranges are not all raw-backed, so section names
alone are not evidence of code.

## Executable Regions

The authoritative classification is in `exe_exec_regions.csv`. The map keeps
raw-backed and virtual-only spaces separate and records entropy, zero density,
and permission flags. A region is not promoted to `CONFIRMED_CODE` merely
because it is executable.

## Entry and Bootstrap

```text
Entry RVA   = 0x0E5DC690
Entry bytes = FF 15 65 C6 9D 0E
IAT slot    = 0x0E9DC665
Boundary    = codoMP_client_shipRetailBase.dll ordinal 1
Continuation= zero-filled padding at 0x0E5DC696
```

The EXE-owned static bootstrap chain is present only as candidate evidence.
CORE-011 observed no post-boundary execution for the historical candidates,
and CORE-013R found no unique static standalone entry.

## Runtime Boundaries

`exe_runtime_boundaries.csv` records source RVA, target, evidence,
confidence, and static/dynamic status. Static chain arrows from EX-045 are
marked `HIGH_CONFIDENCE`; they are not presented as dynamic execution.

## IW4 / CODOL / Tencent Layering

`exe_iw4_signatures.csv` contains only entries with an address or explicit
evidence. `exe_tencent_regions.csv` records whether a region is
platform-only, game-required, or unresolved. No name-only label is treated
as a confirmed engine classification.

## Unknown and Runtime-Generated Space

Large `.tp3` virtual-only ranges and `.tvm0` remain `UNKNOWN` where raw bytes
or callers are absent. They are recorded in `exe_unknown_regions.csv`.

## EXE FINAL ANSWERS

1. **Actual PE structure:** PE32/I386, ImageBase `0x00400000`, six `.tp3`
   sections plus `.tvm0`, with nonstandard section naming.
2. **True code sections:** only regions with direct decode/call evidence are
   code candidates; section executability alone is insufficient.
3. **Protection/unpack/runtime regions:** present as virtual-only or
   non-raw-backed executable space; exact ownership remains `UNKNOWN`.
4. **Entry Point:** a single external ordinal-1 call to
   `codoMP_client_shipRetailBase.dll`.
5. **Ordinal 1 role:** external bootstrap boundary, not a game-runtime entry.
6. **EXE initialization system:** candidate bootstrap/gate/dispatcher chain
   exists, but no confirmed EXE-native caller above `0x77F580`.
7. **IW4/COD6 engine code:** no address-level proof sufficient for
   `CONFIRMED`; relevant signatures remain `HIGH_CONFIDENCE` or `CANDIDATE`.
8. **CODOL-specific code:** network/STUN and platform-gate evidence exists,
   primarily `0x6212C0`, with `CANDIDATE` confidence.
9. **Tencent platform regions:** Base ordinal-1 boundary and platform/network
   callbacks; no broad Tencent module reverse engineering was performed.
10. **Engine initialization chain:** static candidate chain only; dynamic
    execution is `NOT_OBSERVED`.
11. **Renderer/filesystem/network/script/interface:** network candidate is
    present; renderer, filesystem, script, and game-interface entries remain
    `UNKNOWN`.
12. **Game runtime location:** inside the EXE is not proven at an address
    level; no single runtime node satisfies the frozen evidence threshold.
13. **If not in EXE:** the evidence is insufficient to assign another module
    as the game runtime; `.tvm0` or runtime-generated space remains possible.
14. **Standalone prototype boundary:** no unique static boundary is ready.
15. **Most valuable next area:** resolve the `.tp3` virtual-only runtime
    layout and the external ordinal-1 boundary before selecting a prototype
    entry.

## Master Map

```text
codoMP_client_shipRetail.exe
|
+-- PE / Loader                    [CONFIRMED]
+-- Entry Stub                     [CONFIRMED]
+-- External Bootstrap Boundary    [CONFIRMED]
+-- Protection / Packed Regions    [CANDIDATE / UNKNOWN]
+-- Runtime Unpack / Dispatch      [UNKNOWN]
+-- Common Engine                  [UNKNOWN]
+-- IW4 Engine                     [UNKNOWN]
+-- CODOL-specific                 [CANDIDATE]
+-- Tencent-specific               [CANDIDATE]
+-- Game Runtime                   [NOT_PROVEN]
+-- Unknown                        [UNKNOWN]
```

## Evidence Discipline

Every row in the CSV artifacts carries `evidence` and `confidence`. Claims
without direct machine-code or call-relation support are kept `CANDIDATE` or
`UNKNOWN`; no name-based guess is upgraded to `CONFIRMED`.
