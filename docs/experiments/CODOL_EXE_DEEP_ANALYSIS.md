# CODOL_EXE_DEEP_ANALYSIS

## Scope

```text
ANALYSIS = DISK_ARTIFACT_CROSS_ANALYSIS
PROCESS_LAUNCHED = NO
BINARY_MODIFIED = NO
TVM0_RANGE = 0x0E5D3000..0x0E5D7000
RWX_TP3_RANGE = 0x0E5D7000..0x0E659000
DYNAMIC_TEST_READY = NO
```

## Q1 - Packed/virtual to runtime relation

- Unvalidated pointer-like value matches for .tvm0/RWX ranges: `1225`.
- Validated pointer references to .tvm0: `21`.
- Direct frozen CFG edges into .tvm0: `0`.
- Direct frozen CFG edges into RWX .tp3: `1`.
- .tvm0 linear decode ratio: `0.0378`.
- RWX .tp3 linear decode ratio: `0.0010`.
- RWX .tp3 zero rate: `0.1478`.

Result: `UNKNOWN` relationship. There is no evidence-backed path from packed or virtual-only space to an EXE-owned runtime cluster. Mode B applies.

## Q2 - 0x006212C0

```text
RVA = 0x006212C0
SECTION = .tp3
RAW_BACKED_AT_RVA = NO_VIRTUAL_ONLY
STATIC_CLASS = CODOL_SPECIFIC_CANDIDATE
DYNAMIC_CLASS = NOT_OBSERVED
ROLE = NETWORK_STUN_MODE_SELECTION
```

It sits on the historical static candidate chain `0x808650 -> 0x7E98F0 -> 0x6212C0`, but this is not a dynamically observed runtime chain and is not a prototype entry.

## Materialization

The static precondition for the one permitted runtime experiment was not met. No VirtualAlloc/VirtualProtect/new executable page observation is represented as confirmed. All such runtime statuses are `NOT_OBSERVED` or `UNKNOWN`.

## Runtime Layer Model

| Layer | Name | Status | Evidence |
|---:|---|---|---|
| 0 | PE / Loader | CONFIRMED | exe_pe_headers.csv; exe_sections.csv; exe_data_directories.csv; exe_tls.csv |
| 1 | External bootstrap boundary | CONFIRMED | exe_entrypoints.csv; exe_imports.csv; exe_runtime_boundaries.csv |
| 2 | Protection / Packed | CANDIDATE | exe_exec_regions.csv; targeted decode/entropy analysis |
| 3 | Runtime materialization | NO_CONFIRMED_REGION | exe_dynamic_imports.csv UNKNOWN; no materialization pattern in cross evidence |
| 4 | Common engine | NO_CONFIRMED_REGION | exe_iw4_signatures.csv; exe_unknown_regions.csv |
| 5 | IW4-derived engine | NO_CONFIRMED_REGION | exe_iw4_signatures.csv FILE_SYSTEM/RENDERER/ENGINE anchors remain UNRESOLVED |
| 6 | CODOL-specific | CANDIDATE | exe_iw4_signatures.csv; exe_tencent_regions.csv; exe_runtime_candidates.csv |
| 7 | Game runtime | NO_CONFIRMED_REGION | No runtime cluster in exe_cross_evidence.csv |

## Final Answers

**1. .tvm0 nature.** PACKED_CODE is the strongest static classification. It is raw-backed, executable, high-entropy, and lacks a confirmed caller/materialization path; no final claim of encryption or unpack ownership is supported.

**2. writable+executable .tp3 nature.** The section contains a confirmed entry stub and a large reserved RWX tail. The entry stub is code; the section as a whole is not proven game code. The earlier LIKELY_CODE label is narrowed to ENTRY_STUB_PLUS_RESERVED_RWX_SPACE.

**3. relationship.** No confirmed .tvm0 -> .tp3 or .tvm0 -> 0x006212C0 relationship was found. No direct CFG edge or pointer-chain evidence was recovered; relation is UNKNOWN.

**4. runtime materialization.** No confirmed EXE-owned runtime materialization path was found. VirtualAlloc/VirtualProtect/copy/decrypt evidence is NOT_OBSERVED or UNKNOWN, not negative proof.

**5. 0x006212C0 role.** Closest role is CODOL-specific network/STUN mode selection. It is a CANDIDATE leaf on a static bootstrap chain, not a proven runtime entry.

**6. IW4/COD6 cluster.** No address-level IW4/COD6 runtime cluster is confirmed. Filesystem/renderer/engine anchors remain UNRESOLVED.

**7. CODOL-specific cluster.** A small CODOL-specific evidence cluster exists around STUN/network mode selection, but its code is virtual-only in the raw image and dynamically NOT_OBSERVED.

**8. Tencent/platform separation.** Static separation is partial: the Base ordinal-1 boundary and gate/fatal paths are platform-adjacent, while the network/STUN candidate is CODOL-specific but not proven game-runtime.

**9. standalone prototype boundary.** No EXE-native runtime boundary is ready for a standalone prototype. DYNAMIC_TEST_READY remains NO.

**10. blocker.** The blocker is the missing chain from packed/virtual-only regions to materialized executable code, followed by the unresolved external ordinal-1 boundary.

## Current Model

```text
PACKED_REGION
    -> UNPACK / MATERIALIZE      [UNKNOWN]
    -> LIKELY_CODE               [PARTIAL / ENTRY_STUB_ONLY]
    -> RUNTIME DISPATCH          [UNKNOWN]
    -> ENGINE / CODOL            [CANDIDATE]
```

The project is in Mode B: material runtime ownership is not proven inside the EXE from the available disk artifacts, and the packed/virtual-only relationship cannot yet be promoted to a standalone prototype boundary.
