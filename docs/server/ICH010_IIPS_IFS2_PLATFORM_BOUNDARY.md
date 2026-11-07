# ICH-010 — IIPS / IFS2 / ResourceManager Platform Boundary

## Objective

Confirm whether IIPS or IFS2 participates at runtime in the CODOL startup
chain, and whether either reaches the EXE 2.7 MB Game Engine region.

## Evidence Basis

- EX-057 normal `-q` kernel image trace (non-invasive)
- EX-053 IFS2 path causality experiments (3 conditions)
- EX-048/049/060/061/062/063 static PE analysis of `iips.dll`
- ICH-008/009 shared dynamic timeline (3/3 stable runs)

## Runtime Participation

```text
IIPS_RUNTIME_PARTICIPATION = CONFIRMED
```

`iips.dll` was loaded at `2026-09-18 15:35:08.812147` and unloaded at
`15:35:15.306854` (6.49 s window) during a normal `-q` launch observed
by the non-invasive kernel image trace. This is direct dynamic evidence
of module-level participation.

```text
IFS2_RUNTIME_PARTICIPATION = NOT_OBSERVED
```

`IFS2.dll` never appeared in any module snapshot, image-load event, or
thread record across all observations. Three IFS2 path variants
(under IIPS/, beside EXE, independent copy) all produced the same
fatal error without IFS2 loading.

## IIPS-to-IFS2 Handoff

```text
IIPS_TO_IFS2 = NOT_OBSERVED
```

Static evidence confirms that `iips.dll` contains a complete
`CNIFS::initIfsLib` branch:

```text
path construction: <iipsdir> + L"/ifs2.dll"
LoadLibraryW:      iips.dll + 0x96E9
NULL branch:       "Failed to open dllfile"
GetProcAddress:    iips.dll + 0x977C ("CreateIFSLibDll")
indirect call:     iips.dll + 0x97A5
```

No IFS2 image load event occurred between `iips.dll` load and unload.
The dynamic boundary ends at `iips.dll`'s internal status handoff
before the first external dependency call (`LoadLibraryW(ifs2 path)`).

## IFS2-to-Engine

```text
IFS2_TO_ENGINE = NOT_OBSERVED
```

`IFS2.dll` never loaded. No direct or indirect path from IFS2 to the
EXE 2.7 MB Game Engine region can be observed.

## Failure / Return

```text
IIPS/IFS2_FAILURE_OR_RETURN = UNKNOWN
```

The exact failure mechanism inside `iips.dll` that produces
`WIN_IIPS_INIT_ERROR` at `EXE 0x8189FEC` remains unrecovered.
The observed boundary ends at:

```text
iips.dll loaded
  → internal / packed status handoff
  → fatal error
```

without any external dependency handoff being captured.

## Hard Stop Check

No `IFS2 → EXE Engine` path was observed. No Engine-region hit was
recorded in any IIPS-related observation. Hard stop condition met.

