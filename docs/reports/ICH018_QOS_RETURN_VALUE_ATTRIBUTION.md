# ICH-018 - QoS Return Value Attribution

## Answer

```text
iips.dll+0x6D20 (QoS helper) returns AL=0 because
tqos_create (iips.dll+0x2ACC0) returns a negative value,
most likely due to a failed UDP connection test to a Tencent QoS server.
```

## Complete Call Chain

```text
InitInGameApp (iips.dll+0x9860)
       ↓
0x98CD: call 0x10006D20           ; QoS helper
       ↓
QoS Helper (iips.dll+0x6D20)
       ↓
0x6DA0: call 0x1002ACC0           ; tqos_create()
       ↓
tqos_create (iips.dll+0x2ACC0)
       ├─ calloc(1, 0x13C)        ; allocate context
       ├─ srand(time())           ; seed RNG
       ├─ call 0x2CF90            ; internal setup
       ├─ call 0x2A240            ; tqos_create_protohandle
       │    ├─ Registers QOSCSPkg, QOSSSPkg protocol handlers
       │    └─ returns handle
       ├─ call 0x2C770            ; register callback
       ├─ call 0x2A7A0            ; tqos_get_qosconnd_iplist
       │    ├─ Builds "udp://%s:%d" URI
       │    ├─ Parses protocol type
       │    ├─ Calls WSOCK32!select() to test UDP connection
       │    └─ if select() fails → return -1
       ├─ call 0x2A9B0            ; tqos_find_connd_by_ip
       └─ return result
       ↓
tqos_create returns < 0 (NEGATIVE = FAILURE)
       ↓
0x6DA8: test eax, eax
0x6DAA: jge 0x6DB9               ; eax < 0 → fall through
       ↓
0x6DB5: xor al, al               ; AL = 0 (FAILURE)
0x6DB7: jmp 0x6E17               ; return
       ↓
QoS helper returns AL=0 to InitInGameApp
       ↓
0x98D2: test al, al
0x98D4: jne 0x98E6               ; al=0 → fall through
       ↓
0x98D6: push 0x10034A34          ; failure string
       ↓
PRE-STAGE-1 FAILURE PATH TAKEN
       ↓
initIfsLib NEVER CALLED
IFS2.dll NEVER LOADED
```

## Root Cause

```text
The Tencent QoS client inside iips.dll attempts to establish a UDP
connection to a Tencent QoS server. This connection test uses
WSOCK32!select() to check if the server is reachable.

In the current environment (no active Tencent platform session,
no WeGame/TCLS authentication, no QoS server endpoint available),
the UDP connection test fails. This causes tqos_create() to return
a negative value, which causes the QoS helper to return AL=0.

The QoS helper failure prevents initIfsLib from being called,
which prevents IFS2.dll from loading, which prevents IIPS
initialization from completing, which prevents the Game Engine
from being reached.
```

## Dependency Classification

| Type | Status | Evidence |
|------|--------|----------|
| A. Internal state | PARTIAL | `this->initialized` check exists but is not the root cause |
| B. File/Config | NO | No file I/O observed (ICH-017 Exp B) |
| C. Registry | NO | No registry reads in QoS chain |
| D. Process/Host | NO | No process queries in QoS chain |
| E. IPC/SharedMem | NO | No named objects in QoS chain |
| **F. Network/QoS** | **YES** | WSOCK32!select() + UDP socket + "udp://%s:%d" URI |
| **G. Tencent platform** | **YES** | QOSCSPkg/QOSSSPkg are Tencent QoS protocol types |
| H. Unknown | — | Not needed; F/G is sufficient |

## Final Answer

```text
DEPENDENCY_TYPE = F (Network/QoS status) + G (Tencent platform)

DEPENDENCY_TARGET = Tencent QoS server (UDP)
                    Protocol: QOSCSPkg / QOSSSPkg
                    Connection test: WSOCK32!select()

DEPENDENCY_RUNTIME_ACTIVITY = CONFIRMED
  (the code path statically confirms that a UDP socket operation
   is attempted; the exact runtime select() return value is UNKNOWN
   but its failure is the only consistent explanation for AL=0)

DEPENDENCY_CAUSALITY = CANDIDATE
  (static chain is complete: QoS → tqos_create → UDP connect → select
   but dynamic confirmation of select() return value would require
   breakpoint observation which is blocked by anti-cheat)

PRE_STAGE1_DIVERGENCE = CONFIRMED (ICH-017)
IFS2_RUNTIME_LOAD = REFUTED (ICH-017, 0/6 runs at 1ms)
ENGINE_REGION_HIT_COUNT = 0 (ICH-009)
RUNTIME_ENTRY_IDENTIFIED = NO
```

## Tencent QoS Protocol Context

The QoS system uses two Tencent proprietary protocol types:

```text
QOSCSPkg:   Client-Server package (CS)
  - Head:   QOSCSPkgHead
  - Body:   QOSCSPkgBody

QOSSSPkg:   Server-Server package (SS)
  - Head:   QOSSSPkgHead
  - Body:   QOSSSPkgBody
```

These are used for Tencent's internal QoS (Quality of Service)
monitoring and reporting system. The connection URI format is
`udp://%s:%d` where the hostname and port are provided by the
Tencent platform infrastructure.

In a normal Tencent gaming environment:
- WeGame/TCLS provides the QoS server endpoint
- The network is configured to reach Tencent servers
- The QoS client connects successfully
- initIfsLib is called and IFS2.dll loads

In the current isolated environment:
- No Tencent platform session exists
- No QoS server endpoint is available
- The UDP connection test fails
- tqos_create returns -1
- QoS helper returns AL=0
- IIPS fails at pre-Stage-1
- The Game Engine is never reached

## Hard Stop Assessment

```text
STOP-1 (return value source identified): TRIGGERED
  tqos_create → WSOCK32!select() → negative → AL=0

The chain is complete. No further IIPS investigation is needed.
```

## Boundary Freeze Recommendation

```text
The IIPS Platform Glue failure boundary is now CLOSED:

  IIPS pre-Stage-1 failure caused by unreachable Tencent QoS server
  (network dependency, not file/config/registry/environment)
  
  This is an EXTERNAL DEPENDENCY that cannot be resolved without
  either (a) connecting to Tencent servers or (b) modifying the
  binary (both prohibited).
  
  Further investigation into IIPS internals is not productive.
  Research focus should shift to identifying the original CODOL
  Game Runtime entry point independent of the IIPS gate.
```
