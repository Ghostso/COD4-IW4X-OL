# CODOL_EX067_TCLS_SHARED_MEMORY_LAYOUT

## Scope And Corrections

Offline static analysis only. No hook, debugger attach, Frida, API detour,
ETW/runtime instrumentation, IAT/inline/vtable patch, target modification,
fake success, bypass, parameter tampering, injection, or process launch was
performed.

```text
EX-065 command/state interpretation:
SUPERSEDED_BY_EX066

0x16A4DC = primary UpdateProcessor vtable, 17 entries
[this+0x30]/[this+0x34] = 64-bit Game ID
```

Evidence vocabulary:

```text
STATIC_CONFIRMED
STATIC_REACHABLE
STATIC_DATAFLOW_CONFIRMED
STATIC_BOUNDARY
HISTORICAL_DYNAMIC
PACKED_UNRESOLVED
SUPERSEDED
UNKNOWN
```

## Executive Closure

`TCLS_SHAREDMEMEMORY<decimal game PID>` is a 512 KiB named file mapping.
`tcls_core.exe` creates it in `sub_7D10` with a null security DACL,
`PAGE_READWRITE`, and `MapViewOfFile(FILE_MAP_ALL_ACCESS)`.  The producer
writes a version header `0x40` at mapped `+0x00` and initializes a tag/layout
wrapper at `+0x04`, `+0x08`, and `+0x0C`.

`TenProxy.dll` is the game-side endpoint.  `CTclsProxy::Initialize` gets
`GetCurrentProcessId()` at `0x60EF`, builds the same decimal-PID name,
calls `OpenFileMappingW` at `0x61E2`, calls `MapViewOfFile` at `0x6273`,
reads the mapped version from `mapped_base[0]`, and stores:

```text
[object+0x18C4] = mapped_base
[object+0x18C8] = mapped_base + 4
[object+0x18CC] = mapped_base + tag[0x13]
[object+0x18D0] = mapped version
[object+0x18D4] = mapping handle
[object+0x18E0] = initialized
```

The mapped payload is not a flat C struct.  It is a tag container:

```text
mapped + 0x00        dword version/header (0x40)
mapped + 0x04        table of dword tag offsets
entry = mapped + tag_offsets[tag - 1]
entry + 0x00         dword length/type tag
entry + 0x04         payload bytes/wide string
```

TenProxy accesses entries through `this` vtable slots `+0x24` (GetInt),
`+0x28` (GetDWORD), `+0x2C` (GetString), `+0x30` (GetBYTE), and
`+0x34/+0x38` (structured reads).  The recovered GameSignature path reads
tag `0x04` into `object+0x8B0`; the JumpSignature path uses tag `0x1B`
into `object+0xCB4`.  The exact producer-side writers of those tag entries
remain outside the static caller graph.

## Mapped Object

```text
TCLS_SHARED_MEMORY_OBJECT = TCLS_SHAREDMEMEMORY<decimal game PID>
TCLS_SHARED_MEMORY_SIZE = 0x80000 (512 KiB)
TCLS_SHARED_MEMORY_PRODUCER = tcls_core.exe sub_7D10
TCLS_SHARED_MEMORY_CONSUMER = TenProxy.dll CTclsProxy::Initialize
```

Producer name construction:

```text
tcls_core.exe sub_798E
    0x798B  [ebp+0xC] = game PID
    0x798E  L"TCLS_SHAREDMEMEMORY"
    0x7993  L"%s%lu"
    0x799E  format helper
    0x79B0  sub_7D10

tcls_core.exe second construction family
    0x40B6/0x40B9/0x40C9/0x40DC
```

The same `sub_7D10` helper also creates a separate
`RAIL_TCLS_SHARED<LUID>` mapping.  That object is not the PID-keyed
TenProxy mapping and must not be merged with it.

## GamePID Semantics

```text
MAPPING_PID_SOURCE = GetCurrentProcessId in TenProxy; host game-PID argument
PAYLOAD_PID_SOURCE = UNKNOWN
GAMEPID_DATAFLOW = STATIC_DATAFLOW_CONFIRMED
```

The mapping key and the game-side current process ID are the same numeric
value in the recovered path.  No static write of that PID into one of the
mapped tags was recovered.

`TCLS.dll` contains a separate `Clauncher::GetRealGamePID` read path and a
window-discovery path using `GetWindowThreadProcessId` and `OpenProcess`.
Those are distinct PID-discovery mechanisms and are not evidence that the
payload contains the PID.

## GameID Semantics

```text
GAMEID_DATAFLOW = STATIC_DATAFLOW_CONFIRMED
GAMEID_SEMANTIC = 64-bit game identifier; selects game-specific update/repair paths
GAMEID_TO_GAMEPID_RELATION = UNKNOWN / no arithmetic relation recovered
```

The producer is `sub_8A290`:

```text
0x8A340  mov [this+0x30], [ebp+0xC]
0x8A346  mov [this+0x34], [ebp+0x10]
```

`sub_8C6D8` formats the pair as `gameID: %llu`.  `sub_8DBEB` compares the
low half with `0x63`, `0x18`, and `0x11` to select game-specific paths.
`sub_8C783` and `sub_8D2A2` pass the pair into the IIPS configuration and
`CreateIIPSRepair` path.  These values are not command IDs, state IDs, or
mapping-name suffixes.

## TenProxy Initialization Boundary

```text
TENPROXY_INITIALIZE = STATIC_CONFIRMED
TENPROXY_INIT_ENTRY = exported Invoke -> command 0x566 -> sub_13A2 -> sub_5E4A
TENPROXY_INIT_AUTOMATIC = NOT RECOVERED
```

`Invoke` is the only recovered export.  Command `0x566` allocates the
`0x18E4`-byte `CTclsProxy` object and calls the constructor family.
`sub_5E4A` is the full initialization body; no CRT initializer, TLS
callback, `DllMain`, or global constructor path to `sub_5E4A` was recovered.
The upstream caller remains a static boundary.

## Native And TCLS Edges

```text
NATIVE_BOOTSTRAP_TO_TENPROXY = STATIC_BOUNDARY
NATIVE_BOOTSTRAP_TO_TCLS = STATIC_BOUNDARY
BASE_TO_TENPROXY = STATIC_BOUNDARY / PARALLEL_PROTOCOL_PARTICIPANT
CLIENTBASE_TO_TENPROXY = STATIC_BOUNDARY / PARALLEL_PROTOCOL_PARTICIPANT
TENPROXY_TO_TCLS = STATIC_CONFIRMED
TCLS_TO_TENPROXY = STATIC_CONFIRMED
```

`Base.dll` and `ClientBase.dll` contain `TCLS_SHAREDMEMEMORY` literals, but
the recovered evidence does not establish a direct call or import edge to
`TenProxy.dll`.  The protocol is therefore best described as a named-object
participant graph, not a proven C++ call chain.

## Window Protocol

```text
0xBD0   TenProxy -> TCLS core window, wParam=0, lParam=0
0x8889  TCLS.dll -> discovered game window, wParam=0, lParam=0
```

`TCLS_TENPROXY_RESULT` and `TCLS_GMAE_EXIT` are diagnostic labels adjacent
to message paths.  No `RegisterWindowMessageW` call or numeric ID for
`TCLS_TENPROXY_RESULT` was recovered.

## Final Status

```text
TCLS_SHARED_MEMORY_OBJECT = TCLS_SHAREDMEMEMORY<decimal game PID>
TCLS_SHARED_MEMORY_SIZE = 0x80000

TCLS_SHARED_MEMORY_PRODUCER = tcls_core.exe sub_7D10
TCLS_SHARED_MEMORY_CONSUMER = TenProxy.dll CTclsProxy::Initialize

MAPPING_PID_SOURCE = GetCurrentProcessId / host game-PID argument
PAYLOAD_PID_SOURCE = UNKNOWN

GAMEPID_DATAFLOW = STATIC_DATAFLOW_CONFIRMED
GAMEID_DATAFLOW = STATIC_DATAFLOW_CONFIRMED

GAMEID_SEMANTIC = 64-bit game identifier
GAMEID_TO_GAMEPID_RELATION = UNKNOWN

TENPROXY_INITIALIZE = STATIC_CONFIRMED
TENPROXY_INIT_ENTRY = Invoke(0x566) -> sub_13A2 -> sub_5E4A

NATIVE_BOOTSTRAP_TO_TENPROXY = STATIC_BOUNDARY
NATIVE_BOOTSTRAP_TO_TCLS = STATIC_BOUNDARY

BASE_TO_TENPROXY = STATIC_BOUNDARY
CLIENTBASE_TO_TENPROXY = STATIC_BOUNDARY

TENPROXY_TO_TCLS = STATIC_CONFIRMED
TCLS_TO_TENPROXY = STATIC_CONFIRMED

TCLS_PROCESS_CREATION = EXTERNAL_HOST_UNAVAILABLE
TCLS_UPSTREAM_CALLER = EXTERNAL_HOST_UNAVAILABLE

STATIC_BOOTSTRAP_LINK = HOST_PROCESS_BOUNDARY
STATIC_BOOTSTRAP_LINK_TYPE = PID-NAMED-SHARED-MEMORY + TENPROXY_EXPORT_BOUNDARY

RUNTIME_GETRESOURCE_CALL = UNKNOWN
RUNTIME_INITINGAMEAPP = UNKNOWN
RUNTIME_IFS2_LOAD = UNKNOWN
RUNTIME_CREATEIFS = UNKNOWN
RUNTIME_FIRST_FAILURE = UNKNOWN
```

## Remaining Unknowns

```text
U01  The exact host-side tag writers for fields observed by TenProxy.
U02  The producer-side source of GameID passed to UpdateProcessor::Update.
U03  Any runtime relation between GamePID and GameID.
U04  The exact caller of the exported TenProxy Invoke dispatcher.
U05  The numeric message ID corresponding to TCLS_TENPROXY_RESULT.
U06  Whether an external/packed bootstrap performs TenProxy loading in a
     form not expressible in the available static import/export graph.
```
