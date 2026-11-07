# ICH-013 - IIPS Status Flow

## Complete Status Diagram

```text
[STATUS SOURCE]
  UNKNOWN (packed/VM computation inside EXE .tp3 virtual-only region)
       |
       v
[IIPS RESULT]
  iips.dll CNIFS::initIfsLib fails
  (one of: LoadLibraryW failure / GetProcAddress failure /
           CreateIFSLibDll failure / DestoryIFSLibDll failure)
  exact failing stage at runtime = UNKNOWN
       |
       v
[0x8189FEC]
  runtime-computed value (not a memory address)
  produced by EXE packed .tp3 code
  no static reference in any module
       |
       v
[WIN_IIPS_INIT_ERROR]
  EXE string at VA 0xDC93A8
  consumed by packed/VM code (0 static native refs)
  displayed via "0x%x" formatter (VA 0xDC9400)
  push site at VA 0x0058F281 (packed code, call target virtual-only)
       |
       v
[FAILURE]
  IIPS initialization failed
  iips.dll unloads (~6.49s window)
  no IFS2.dll ever loaded
       |
       v
[NEXT TARGET]
  Process terminates with 0xC0000409 (fail-fast)
  EXE 2.7 MB Game Engine region NEVER REACHED
  ENGINE_REGION_HIT_COUNT = 0
```

## Success Path (statically identified, dynamically NOT_OBSERVED)

```text
initIfsLib returns AL=1 (all 4 stages pass)
       |
       v
InitInGameApp test al at 0x99D7, jne 0x9A2B (success branch)
       |
       v
0x9A2B: mov ecx, [ebp+0x60]      ; IFS object ptr
0x9A2E: mov eax, [ecx]            ; vtable
0x9A30: mov edx, [eax+0x2C]      ; vtable slot 0x2C
0x9A33: push 1                    ; status = IIPS_INIT_OK
0x9A35: call edx                  ; inside IFS2.dll (NOT EXE Engine)
       |
       v
0x9A37..0xA831: Resource manager setup
  ShareState_MMF / mutex
  HostApp config
  Path construction
       |
       v
0xA831: mov al, 1                  ; InitInGameApp SUCCESS
0xA833: cleanup, ret 0x38
       |
       v
Return to caller (Base.dll .tvm0 or EXE packed code)
       |
       v
EXE 2.7 MB Game Engine: NOT_OBSERVED from this path
```

## Static Failure Branch Table (iips.dll)

| Stage | RVA | Failure String | [ebp+0xCC] Value | Return |
|-------|-----|---------------|------------------|--------|
| LoadLibraryW | 0x96E9 | "Failed to open dllfile" | 1 | AL=0 |
| GetProcAddress(CreateIFSLibDll) | 0x977C | "Failed to get function CreateIFSLibDll" | 2 | AL=0 |
| CreateIFSLibDll() | 0x97A5 | "Failed to create ifs lib" | 1 | AL=0 |
| GetProcAddress(DestoryIFSLibDll) | 0x97CC | "Failed to get proc DestoryIFSLibDll" | 3 | AL=0 |

All four failure branches converge to:
```text
0x9726, cleanup, 0x9769, xor al,al, jmp 0x9839, ret 0x20
```

## Runtime Evidence Boundary

```text
DYNAMICALLY CONFIRMED:
  iips.dll loads and unloads (EX-057 kernel image trace)
  IFS2.dll never loads (EX-057, EX-053, ICH-010)
  WIN_IIPS_INIT_ERROR / 0x8189FEC appears as fatal error (multiple runs)
  Process terminates 0xC0000409

DYNAMICALLY UNKNOWN:
  Which initIfsLib stage fails at runtime (1/2/3/4)
  The exact expression that produces 0x8189FEC
  Whether the failure originates inside IIPS or from a VM/Platform status

STATICALLY CONFIRMED:
  Complete 4-stage gate structure in iips.dll initIfsLib
  Complete success branch in iips.dll InitInGameApp
  WIN_IIPS_INIT_ERROR / "0x%x" formatter in EXE packed code
  0 static references to 0x8189FEC as address or immediate
```
