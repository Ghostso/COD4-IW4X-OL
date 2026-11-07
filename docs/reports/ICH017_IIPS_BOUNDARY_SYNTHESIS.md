# ICH-017 - IIPS Boundary Synthesis (ICH-013 through ICH-017)

## Consolidated Research Boundary

### Evidence Chain Summary

| Round | Question | Answer | Evidence Level |
|-------|----------|--------|---------------|
| ICH-008 | VM → Native transfer? | YES (Platform Glue) | DYNAMIC_CONFIRMED |
| ICH-009 | Platform → Engine? | NO (0/439 events) | DYNAMIC_CONFIRMED_ABSENCE |
| ICH-010 | IIPS → IFS2? | IIPS loads, IFS2 never does | DYNAMIC_CONFIRMED |
| ICH-011 | BugTrace role? | Platform/anti-cheat, NOT IIPS bridge | DYNAMIC_CONFIRMED |
| ICH-012 | Unknown Native Layer? | RESOLVED (Base .tvm0) | DYNAMIC_CONFIRMED |
| ICH-013 | IIPS gate semantics? | 0x8189FEC = runtime-computed failure value | STATIC_CONFIRMED |
| ICH-014 | Four-stage pre-conditions? | ALL SATISFIED statically | STATIC_CONFIRMED |
| ICH-015 | Debugger observability? | BLOCKED (anti-cheat prevents iips.dll load) | DYNAMIC_CONFIRMED |
| ICH-016 | Normal startup loader? | iips loads 3/3, IFS2 loads 0/3 | DYNAMIC_CONFIRMED |
| ICH-017 | Sub-ms transient IFS2? | REFUTED (0/3 at 1ms resolution) | DYNAMIC_CONFIRMED |

### Refined Startup Boundary

```text
┌─────────────────────────────────────────────────────────────────┐
│ CONFIRMED                                                       │
│                                                                 │
│  CODOL EXE starts                                              │
│    → EXE Entry (RVA 0xE5DC690)                                 │
│    → Base.dll ordinal-1 → .tvm0 VM Dispatcher                   │
│    → BugTrace.dll (Platform/anti-cheat)                        │
│    → TenProxy.dll, GbSpy.dll (Platform proxy)                  │
│    → iips.dll IMAGE_LOAD (3/3 stable)                          │
│    → IIPS initialization begins                                │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ PRE-STAGE-1 DIVERGENCE REGION (failure occurs here)            │
│                                                                 │
│  InitInGameApp (iips.dll+0x9860)                               │
│    → QoS helper (iips.dll+0x6D20) called at +0x98CD            │
│    → test al,al at +0x98D2                                     │
│    → if al=0: error branch → failure (← MOST LIKELY)          │
│    → if al!=0: continue to initIfsLib                          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ NEVER REACHED (refuted by 1ms resolution, 0/6 runs)            │
│                                                                 │
│  initIfsLib (iips.dll+0x9570)                                   │
│    → Stage 1: LoadLibraryW("IFS2.dll") at 0x96E9              │
│    → Stage 2: GetProcAddress("CreateIFSLibDll") at 0x977C     │
│    → Stage 3: CreateIFSLibDll() at 0x97A5                     │
│    → Stage 4: GetProcAddress("DestoryIFSLibDll") at 0x97CC    │
│    → SUCCESS: AL=1                                              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ CONFIRMED (after IIPS failure)                                  │
│                                                                 │
│  WIN_IIPS_INIT_ERROR (0x8189FEC)                               │
│    → Process termination (0xC0000409)                          │
│    → EXE 2.7 MB Game Engine: NEVER REACHED                     │
│    → ENGINE_REGION_HIT_COUNT = 0                               │
└─────────────────────────────────────────────────────────────────┘
```

### Primary Blocking Boundary (Final)

```text
PRIMARY_BLOCKING_BOUNDARY = 
  IIPS pre-Stage-1 control flow divergence

  Specifically: the conditional branch at iips.dll+0x98D2
  (test al,al after QoS helper call at iips.dll+0x98CD)
  
  When this branch takes the failure path (al=0), initIfsLib
  is never called, IFS2.dll is never loaded, and IIPS reports
  initialization failure to the EXE.
```

### What Has Been Definitively Established

```text
CONFIRMED:
  1. VM dispatches to Platform, not Engine (ICH-008/009)
  2. IIPS module loads and begins initialization (ICH-010/016/017)
  3. IFS2.dll satisfies all static pre-conditions (ICH-014)
  4. IFS2.dll is NEVER loaded at runtime (ICH-010/016/017: 0/6+ runs)
  5. No transient sub-ms IFS2 load exists (ICH-017: 1ms, 0/3)
  6. Debugger observation is blocked by anti-cheat (ICH-015)
  7. IFS2 path changes produce no outcome change (EX-053)
  8. The failure occurs before LoadLibraryW("IFS2.dll") is called
  9. No file system activity in IIPS directory during launch (ICH-017)
 10. The EXE 2.7MB Game Engine region is never reached (ICH-009)
```

### What Remains UNKNOWN

```text
UNKNOWN:
  1. What exact condition the QoS helper checks
  2. What value the QoS helper returns and why
  3. Whether other pre-initIfsLib conditions exist beyond QoS
  4. The exact mapping from IIPS internal failure to 0x8189FEC
  5. What would make the QoS helper return non-zero (success)
```

### Excluded Components

| Component | Excluded By |
|-----------|------------|
| IFS2.dll file missing | ICH-014 (file exists) |
| IFS2.dll wrong architecture | ICH-014 (x86, correct) |
| IFS2.dll missing exports | ICH-014 (both exports present) |
| IFS2.dll missing dependencies | ICH-014 (all system DLLs) |
| IFS2.dll path visibility | EX-053 (3 paths, no change) |
| Sub-ms transient IFS2 load | ICH-017 (1ms, 0/3) |
| Unknown Native Layer | ICH-009 (resolved to Base .tvm0) |
| BugTrace → IIPS bridge | ICH-011 (no shared call chain) |
| Engine region reached | ICH-009 (0/439 events) |
| Debugger-side observation | ICH-015 (anti-cheat blocks iips.dll) |
| File system precondition | ICH-017 Exp B (0 file events) |

### Next Research Direction

The only remaining path forward is to identify the precondition that
the QoS helper (iips.dll+0x6D20) checks. This requires either:

1. **Static analysis of iips.dll+0x6D20** (limited, since it is inside
   iips.dll and the task has been avoiding full IIPS reverse engineering)

2. **External state correlation at microsecond resolution** (using
   kernel ETW with Process/Thread/Registry/File events, filtered to
   the 500ms window around iips.dll load)

3. **Controlled single-variable experiments** (modify one external
   condition at a time and observe whether the outcome changes)

Approach 3 is the most likely to produce a definitive answer within
the current constraint set, but requires knowing which conditions to
test.

### Conclusion

```text
The CODOL startup failure is definitively attributed to:

  IIPS pre-Stage-1 control flow divergence
  (inside iips.dll, after module load, before IFS2 dependency call)

This is NOT:
  - An IFS2 loading problem (IFS2 is never attempted)
  - A BugTrace/anti-cheat failure (BugTrace works correctly)
  - A VM dispatch failure (VM works correctly)
  - A missing platform component (all platform DLLs load)
  - A Game Engine problem (Engine is never reached)

The blocking boundary is INSIDE iips.dll's own initialization logic,
specifically in the code path between InitInGameApp entry and the
call to initIfsLib. The most likely specific point is the QoS helper
conditional branch at iips.dll+0x98D2.
```
