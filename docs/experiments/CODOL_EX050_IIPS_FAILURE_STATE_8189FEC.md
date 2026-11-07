# EX-050 IIPS Failure-State and `8189FEC` Source Chain

## Final Classification

```text
IIPS_INIT_FUNCTIONS_PARTIAL
CREATE_IFS_FAILURE_BRANCH_L2_CONFIRMED
IIPS_ERROR_STRING_CALLERS_RECONSTRUCTED
IIPS_ERROR_STATE_DATAFLOW_CONFIRMED
8189FEC_SOURCE_STATIC_UNCONFIRMED
IIPS_TO_EXE_ERROR_BOUNDARY_UNCONFIRMED
TVM0_BOUNDARY
NEW_EXECUTION_NODE_NONE
```

The IIPS-to-IFS2 failure branch is now statically reconstructed inside
`iips.dll`. The exact source of `8189FEC` remains unresolved and lies
outside the reachable plaintext/static boundary; no `.tvm0` reverse
engineering was attempted.

## P0: `0x100097A5` Failure Branch

The call site is:

```asm
0x100097A5  call eax                   ; eax = CreateIFSLibDll
0x100097A7  test eax, eax
0x100097A9  mov [ebp+0x60], eax
0x100097AC  jne 0x100097C3             ; success / next prerequisite
```

Failure path:

```asm
0x100097AE  push 0x100349B4            ; "Failed to create ifs lib"
0x100097B3  lea eax, [ebp+0x64]
0x100097B6  call 0x10004310            ; append/error-store helper
0x100097BB  add esp, 4
0x100097BE  jmp 0x1000971C
```

This confirms the L2 branch:

```text
CreateIFSLibDll
  -> test eax,eax
  -> jne success/next
  -> else "Failed to create ifs lib"
```

## Resolver Failure Branches

```asm
0x10009770  mov esi, [0x10033014]      ; GetProcAddress
0x10009776  push 0x10034964            ; "CreateIFSLibDll"
0x1000977B  push eax
0x1000977C  call esi
0x1000977E  test eax,eax
0x10009783  jne 0x100097A1             ; call CreateIFSLibDll

0x10009785  push 0x10034974            ; "Failed to get function CreateIFSLibDll"
```

Destroy resolver failure:

```asm
0x100097CC  call esi                   ; GetProcAddress("DestoryIFSLibDll")
0x100097D3  jne 0x100097F4
0x100097D5  push 0x100349F8            ; "Failed to get proc DestoryIFSLibDll"
```

## Function Boundary Status

```text
FUNCTION_BOUNDARY_PARTIAL
```

The resolver/call wrapper is a single contiguous error-handling region
around `iips.dll RVA 0x9570..0x9860`. Exact function start/end require a
clean prologue analysis, which was not fully recovered.

## IIPS Error String Callers

String references found in `iips.dll` `.text`:

```text
"Failed to get function CreateIFSLibDll" -> RVA 0x9785
"Failed to create ifs lib"               -> RVA 0x97AE
"Failed to get proc DestoryIFSLibDll"    -> RVA 0x97D5
```

The three branches are distinct and locally recoverable.

## IIPS Error State Dataflow

Observed dataflow:

```text
GetProcAddress(CreateIFSLibDll)
  -> stored at [ebp+0x58]
  -> called via EAX
  -> return stored at [ebp+0x60]
  -> tested immediately

GetProcAddress(DestoryIFSLibDll)
  -> stored at [ebp+0x5C]
```

No static mapping to `8189FEC` was found.

## `IIPSERR_*` Strings

Found:

```text
IIPSERR_CACHE_INIT
IIPSERR_ERROR_INIT
```

No direct pointer xrefs were found for these names in `.text`. They may
be log/status labels rather than direct error-code values.

No evidence connects them to `8189FEC`.

## EXE Error Boundary

EXE strings:

```text
WIN_IIPS_INIT_ERROR
WIN_IIPS_INIT_FAILED
WIN_IIPS_DLL_ERROR
IIPS\iips.dll
Environment List Box
```

They are located in the packed EXE error-data cluster. No plain `.text`
callsite was recovered:

```text
IIPS_TO_EXE_ERROR_BOUNDARY_UNCONFIRMED
EXE_ERROR_FORMATTER_TVM0_BOUNDARY
```

## `8189FEC` Source Search

Searched exact and nearby values:

```text
8189FEC, 8189FD, 8189FE, 8189FF, 8189FC
```

No plaintext constant was found in the recoverable IIPS/IFS2/EXE surface.

```text
8189FEC = PACKED_OR_RUNTIME_GENERATED
```

## Answers

1. After `0x100097A5 call eax`: `test eax,eax`, store to `[ebp+0x60]`, jump to success on nonzero.
2. Failure branch: `RVA 0x97AE` pushes `"Failed to create ifs lib"`.
3. L2 proof of that branch to the error string: YES.
4. IIPS init failure states: resolver failure, create failure, destroy-proc failure; broader state table partial.
5. States entering `WIN_IIPS_INIT_ERROR`: unproven at EXE boundary.
6. IIPS-to-EXE error-code handoff: unresolved at packed boundary.
7. Static recovery path for `8189FEC`: no.
8. `8189FEC` remains `PACKED_OR_RUNTIME_GENERATED`.
9. IFS2 remains a candidate prerequisite, not a proven root cause.
10. New execution node: no.
11. TVM0 boundary: yes, for exact `8189FEC`/EXE error formatter source.
12. Next round: continue static IIPS prerequisite analysis, not `.tvm0` internals.

## Final

```text
IIPS_INIT_FUNCTIONS_PARTIAL
CREATE_IFS_FAILURE_BRANCH_L2_CONFIRMED
IIPS_ERROR_STRING_CALLERS_RECONSTRUCTED
IIPS_ERROR_STATE_DATAFLOW_CONFIRMED
8189FEC_SOURCE_STATIC_UNCONFIRMED
IIPS_TO_EXE_ERROR_BOUNDARY_UNCONFIRMED
TVM0_BOUNDARY
NEW_EXECUTION_NODE_NONE
```
