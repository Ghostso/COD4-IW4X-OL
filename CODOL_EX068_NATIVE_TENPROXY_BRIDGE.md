# CODOL_EX068_NATIVE_TENPROXY_BRIDGE

## Scope

Offline static analysis only. No hook, debugger attach, Frida, API detour,
ETW/runtime instrumentation, IAT/inline/vtable patch, target modification,
fake payload, fake success, bypass, injection, or process launch was
performed.

Evidence vocabulary:

```text
STATIC_CONFIRMED
STATIC_REACHABLE
STATIC_DATAFLOW_CONFIRMED
STATIC_BOUNDARY
HISTORICAL_DYNAMIC
PACKED_UNRESOLVED
STRING_ONLY
UNKNOWN
SUPERSEDED
```

## Executive Closure

The game-side TenProxy entry is statically confirmed:

```text
codoMP_client_shipRetailBase.dll
    GetTSObject
    TenProxy.dll
    Invoke
        |
        v
TenProxy.dll!Invoke
    0x13E3 -> 0x1D70
        |
        v
    command 0x566
        |
        v
    allocate 0x18E4-byte CTclsProxy
        |
        v
    sub_13A2 -> CTclsProxy::Initialize
```

`Base.dll` contains the complete `GetTSObject` / `TenProxy.dll` / `Invoke`
tuple and the `LoadLibraryA`/`GetProcAddress` imports used by its dynamic
import descriptor.  This establishes a static, game-side loader route to
the exported TenProxy dispatcher.  It does not establish a direct ordinary
import edge from `codoMP_client_shipRetail.exe` itself.

The executable contains the same strings and the `0x566` command template,
but the bytes are inside the packed TP3/VM dispatcher.  Those bytes are
classified `PACKED_UNRESOLVED`, not as a proved `call`.

## TenProxy Initialization

```text
TENPROXY_INVOKE_CALLER = GAME_SIDE_DYNAMIC_IMPORT_DESCRIPTOR (Base.dll)
TENPROXY_INIT_TRIGGER = Invoke command 0x566
TENPROXY_INIT_CONTEXT = allocate 0x18E4-byte CTclsProxy; sub_13A2 -> sub_5E4A
```

The only recovered export is `Invoke`.  The dispatcher compares the first
argument with `0x566`, allocates the proxy object, and enters the constructor
family.  This is a command selector, not a named or ordinal C++ interface.

## Shared-Memory Producer

```text
TCLS_SHARED_MEMORY_CREATOR = tcls_core.exe sub_7D10
TCLS_SHARED_MEMORY_GAME_SIDE = TenProxy.dll CONSUMER
TCLS_SHARED_MEMORY_OBJECT = TCLS_SHAREDMEMEMORY<decimal game PID>
TCLS_SHARED_MEMORY_SIZE = 0x80000
```

`TenProxy.dll` computes the suffix with `GetCurrentProcessId`, opens the
named object at `0x61E2`, maps it at `0x6273`, and reads the tag container.
No `CreateFileMapping*` or `OpenFileMapping*` producer path for this object
was recovered in the analyzed CODOL game-side images.  The creator remains
the TCLS host.

## GamePID

```text
GAMEPID_SOURCE = GetCurrentProcessId on the TenProxy side; host game-PID argument on the tcls_core side
GAMEPID_DATAFLOW = STATIC_DATAFLOW_CONFIRMED
PAYLOAD_GAMEPID = UNKNOWN
```

The PID is the mapping-name key.  No write of that PID into the mapped
payload was recovered.

## GameID

```text
GAMEID_SOURCE = UpdateProcessor::Update arguments
GAMEID_GENERATION = EXTERNAL_HOST_UNKNOWN
GAMEID_DATAFLOW = STATIC_DATAFLOW_CONFIRMED
GAMEID_STORAGE = tcls_core [this+0x30]/[this+0x34]
GAMEID_SHARED_MEMORY_TAG = NOT_RECOVERED
```

`sub_8A290` writes the two 32-bit halves into `[this+0x30]` and
`[this+0x34]`.  `sub_8C6D8` formats the pair as `gameID: %llu`, and
`sub_8DBEB` compares the low half against `0x63`, `0x18`, and `0x11`.
The producer of the original 64-bit value is still upstream of the
recovered TCLS host code.

## GameSignature

```text
GAMESIGNATURE_SOURCE = TCLS shared-memory tag 0x04, producer UNKNOWN
GAMESIGNATURE_DATAFLOW = CONSUMER STATIC_DATAFLOW_CONFIRMED
GAMESIGNATURE_SEMANTIC = OPAQUE_BLOB
```

TenProxy reads tag `0x04`, stores the length/state in `object+0x8AC`, and
copies the payload into `object+0x8B0`.  No producer-side writer was found
in the analyzed game-side images.  The payload is not assumed to be text.

## JumpSignature

```text
JUMPSIGNATURE_SOURCE = TCLS shared-memory tags 0x1A/0x1B, producer UNKNOWN
JUMPSIGNATURE_DATAFLOW = CONSUMER STATIC_DATAFLOW_CONFIRMED
JUMPSIGNATURE_SEMANTIC = OPAQUE_BLOB
```

TenProxy reads the selector/header tag `0x1A` and payload tag `0x1B` into
the `object+0xCB4` buffer.  No producer-side writer was found.  No text,
RVA, hash, or address interpretation is asserted without further evidence.

## Native Boundary

```text
NATIVE_BOOTSTRAP_TO_TENPROXY = STATIC_REACHABLE_VIA_BASE_DYNAMIC_IMPORT_DESCRIPTOR
NATIVE_BOOTSTRAP_TO_TCLS = PACKED_UNRESOLVED

BASE_TO_TENPROXY = STATIC_REACHABLE
CLIENTBASE_TO_TENPROXY = STATIC_BOUNDARY
```

The base module is the concrete game-side loader participant.  The
executable's packed stream contains the same bridge constants but cannot be
promoted to a direct static call without a recovered unpacked dispatch.

## IIPS Consumption

```text
IIPS_CONSUMES_GAMEID = STATIC_DATAFLOW_CONFIRMED (tcls_core -> CreateIIPSRepair context)
IIPS_CONSUMES_GAMESIGNATURE = STATIC_BOUNDARY
IIPS_CONSUMES_JUMPSIGNATURE = STATIC_BOUNDARY
```

The analyzed IIPS images do not contain a recovered shared-memory read or a
direct argument flow from either signature tag.

## Final Status

```text
TENPROXY_INVOKE_CALLER = codoMP_client_shipRetailBase.dll dynamic import descriptor
TENPROXY_INIT_TRIGGER = Invoke(0x566)
TENPROXY_INIT_CONTEXT = allocation + sub_13A2 -> CTclsProxy::Initialize

TCLS_SHARED_MEMORY_CREATOR = tcls_core.exe sub_7D10
TCLS_SHARED_MEMORY_GAME_SIDE = TenProxy.dll CONSUMER

GAMEPID_SOURCE = GetCurrentProcessId / host game-PID argument
GAMEPID_DATAFLOW = STATIC_DATAFLOW_CONFIRMED

GAMEID_SOURCE = UpdateProcessor arguments / external host
GAMEID_GENERATION = UNKNOWN
GAMEID_DATAFLOW = STATIC_DATAFLOW_CONFIRMED

GAMESIGNATURE_SOURCE = UNKNOWN PRODUCER / tag 0x04
GAMESIGNATURE_DATAFLOW = CONSUMER STATIC_DATAFLOW_CONFIRMED

JUMPSIGNATURE_SOURCE = UNKNOWN PRODUCER / tags 0x1A/0x1B
JUMPSIGNATURE_DATAFLOW = CONSUMER STATIC_DATAFLOW_CONFIRMED

NATIVE_BOOTSTRAP_TO_TENPROXY = STATIC_REACHABLE
NATIVE_BOOTSTRAP_TO_TCLS = PACKED_UNRESOLVED

BASE_TO_TENPROXY = STATIC_REACHABLE
CLIENTBASE_TO_TENPROXY = STATIC_BOUNDARY

TENPROXY_TO_TCLS = STATIC_CONFIRMED
TCLS_TO_TENPROXY = STATIC_CONFIRMED

IIPS_CONSUMES_GAMEID = STATIC_DATAFLOW_CONFIRMED
IIPS_CONSUMES_GAMESIGNATURE = STATIC_BOUNDARY
IIPS_CONSUMES_JUMPSIGNATURE = STATIC_BOUNDARY

NATIVE_TENPROXY_BOUNDARY = BASE_DYNAMIC_IMPORT_DESCRIPTOR
STATIC_BOOTSTRAP_LINK = GAME_BASE_DLL_TO_TENPROXY_EXPORT
STATIC_BOOTSTRAP_LINK_TYPE = DYNAMIC_OBJECT_LOADER + COMMAND_0x566

TCLS_PROCESS_CREATION = EXTERNAL_HOST_UNAVAILABLE

RUNTIME_GETRESOURCE_CALL = UNKNOWN
RUNTIME_INITINGAMEAPP = UNKNOWN
RUNTIME_IFS2_LOAD = UNKNOWN
RUNTIME_CREATEIFS = UNKNOWN
RUNTIME_FIRST_FAILURE = UNKNOWN
```

## Remaining Unknowns

```text
U01  The exact unpacked instruction in codoMP_client_shipRetail.exe that calls Invoke(0x566).
U02  The host-side writers for mapped tags 0x04, 0x1A, and 0x1B.
U03  The upstream source/generation of the 64-bit GameID.
U04  Whether the two signatures have a text, hash, RVA, or binary semantic.
U05  Any direct IIPS dataflow consuming the two signature tags.
U06  The external process that creates tcls_core and supplies its game-PID argument.
```
