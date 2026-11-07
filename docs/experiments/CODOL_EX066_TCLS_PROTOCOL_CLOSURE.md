# CODOL_EX066_TCLS_PROTOCOL_CLOSURE

## Scope

Offline static analysis only. No hook, detour, debugger attach, Frida, ETW
runtime instrumentation, IAT/inline/vtable patch, target modification, fake
success, bypass, parameter tampering, or process launch was performed.

Evidence vocabulary used here:

```text
STATIC_CONFIRMED
STATIC_REACHABLE
STATIC_DATAFLOW_CONFIRMED
STATIC_BOUNDARY
HISTORICAL_DYNAMIC
PACKED_UNRESOLVED
UNKNOWN
```

## Executive Answer

```text
Game PID producer/source:
    tcls_core.exe receives the launched game PID as an argument and formats
    TCLS_SHAREDMEMEMORY<decimal PID> at 0x798B/0x40B6.

Game mapping producer:
    tcls_core.exe builds the name and calls sub_7D10; the name is keyed by
    the game PID.

Game-side consumer:
    TenProxy.dll calls GetCurrentProcessId at 0x60EF, builds the same prefix,
    opens it with OpenFileMappingW at 0x61E2, and maps it at 0x6273.

Host/window IPC:
    TCLS core owns TCLS_CORE_WND_%u (0x18F57) and named core objects.
    TenProxy posts numeric messages, including 0xBD0, to its discovered
    TCLS window.

IIPS:
    tcls_core.exe dynamically resolves and calls CreateIIPSRepair at
    0x8D353/0x8D38A/0x8D39F.

Native bootstrap:
    No static CALL/import/vtable/function-pointer edge from the CODOL native
    bootstrap to TenProxy/Base was found.  The protocol edge is named-object
    based.
```

## Phase 1 - TCLSHostApp Object Model

`sub_89EEE` is the constructor/initializer family.  It writes three vtable
pointers at object offsets `+0`, `+4`, and `+8`:

```text
[this+0] = 0x56A4DC   17 entries, primary table
[this+4] = 0x56A524    4 entries, callback/secondary table
[this+8] = 0x56A538    1 entry, secondary table
```

The `0x16A4DC` region is therefore a vtable, not an array of records with
embedded command IDs.  The target addresses in the primary table are:

```text
0 sub_901E5
1 sub_9062B
2 sub_8DBEB
3 sub_8E9BB
4 sub_90636
5 sub_9063F
6 sub_8DE6E
7 sub_90622
8 sub_90619
9 sub_8EAD2
10 sub_8D9EF
11 sub_90648
12 sub_90653
13 sub_8DB11
14 sub_9065C
15 sub_8EA06
16 sub_8EA46
```

The constructor also initializes `+0x18` (initialized flag), `+0x1C`,
`+0x20`, `+0x24`, `+0x25` (mode flags), the 64-bit field at `+0x30/+0x34`,
and the IIPS module/result fields at `+0x5268/+0x526C`.

### Correction to the provisional EX-065 interpretation

`[this+0x30]` and `[this+0x34]` are not command IDs, state IDs, or message
IDs.  `sub_8C6D8` formats this pair with:

```text
L"UpdateProcessor::InternalUpdateFailed(), gameID: %llu, ..."
```

The literal comparisons in the two handlers are against game IDs:

```text
0x63, 0x18, 0x11
```

They select game-specific update/repair paths when the upper 32-bit half is
zero.  They are not command-table entries and do not by themselves establish
a command/state/message mapping.

## Phase 2 - The two sub_8D2A2 callers

Direct callers are exactly:

```text
0x8DA49 in sub_8D9EF
0x8DE3C in sub_8DBEB
```

`sub_8D2A2` receives `this` in `ECX`, has no pushed stack arguments at either
call site, and uses `[this+0x30/+0x34]` only as context passed to `sub_8C8CF`.
It stores the loaded module at `[this+0x5268]`, resolves
`CreateIIPSRepair` at 0x8D38A, calls it at 0x8D39F, and stores the returned
object at `[this+0x526C]`.  `EAX` is the returned object pointer; the caller
continues using the same `this` object.

## Phase 3 - TCLS core named objects

```text
TCLS_CORE_SHARE_MEMORY_%s%s   tcls_core.exe 0xC629
TCLS_CORE_MUTEX_%s%s          tcls_core.exe 0xC77F
TCLS_CORE_WND_%u              tcls_core.exe 0x18F57
TCLS_EXIT_EVENT               tcls_core.exe 0x1B571 / 0x1C1DB
```

The core shared-memory and mutex names are built by `sprintf`-style helper
`sub_4077F0` and receive their suffix through the surrounding object.  The
recovered core producer/consumer call sites include `CreateFileMappingW`
0x7D81/0x7ED1/0xC4F7 and the mutex site at 0x8C854.  These are not the
game-PID keyed game context.

## Phase 4 - TCLS_SHAREDMEMEMORY + Game PID

Producer side in `tcls_core.exe`:

```text
0x798B  push [ebp+0xC]              game PID argument
0x798E  push L"TCLS_SHAREDMEMEMORY"
0x7993  push L"%s%lu"
0x799E  call sub_4077F0             sprintf
0x79B0  call sub_7D10              open/create mapping
```

The same construction exists at `0x40B6/0x40B9/0x40C9/0x40DC`.

Consumer side in `TenProxy.dll`:

```text
0x60EF  call GetCurrentProcessId
0x6157  build decimal PID
0x61B4/0x61C7 build TCLS_SHAREDMEMEMORY<pid>
0x61E2  call OpenFileMappingW
0x6273  call MapViewOfFile
```

`GetCurrentProcessId` is therefore directly part of the object-name suffix
on the game side.  The historical log at
`工具/EX035_DIR/TenproxyLog/20201216_215111.log` shows PID 4540 and
`TCLS_SHAREDMEMEMORY+4540`, but is only `HISTORICAL_DYNAMIC`.

## Phase 5 - GamePID Flow

```text
launcher / TCLS host
    -> game PID argument [ebp+0xC]
    -> tcls_core sub_798E / sub_40B9
    -> TCLS_SHAREDMEMEMORY<decimal PID>

CODOL game process
    -> GetCurrentProcessId (TenProxy 0x60EF)
    -> same named mapping
    -> MapViewOfFile (0x6273)
    -> mapped context
```

`TCLS.dll` contains the `[Clauncher::GetRealGamePID]` read path and opens a
file mapping/read structure before returning its PID.  The exact final
caller storage is not fully resolved in this round; it is classified as
`STATIC_CONFIRMED` for the reader path and `UNKNOWN` for the complete
downstream storage chain.

`TCLS.dll` also discovers a game window using `FindWindowW`/static
`GetWindowThreadProcessId` and opens the process at 0x88CEC.  That path
proves a separate PID-discovery mechanism, but it is not the same operation
as `GetRealGamePID` and is not used to name the mapping.

## Phase 6 - Window and Message Protocol

```text
tcls_core 0x18F57  TCLS_CORE_WND_%u
TenProxy  0x7BA0   FindWindowW("static", object field +0x49C)
TenProxy  0x7BBC   PostMessageW(hwnd, 0xBD0, 0, 0)  ; TCLS_GMAE_EXIT
TenProxy  0x7C0A   FindWindowExW(...)
TCLS.dll  0x88C90  FindWindowW(...)
TCLS.dll  0x88D84  PostMessageW(hwnd, 0x8889, 0, 0)
```

The `TCLS_TENPROXY_RESULT` and `TCLS_GMAE_EXIT` literals are diagnostic
labels near the message paths.  They are not registered window-message
strings.  Resolved numeric IDs are:

```text
0xBD0   TenProxy -> TCLS core window
0x8889  TCLS.dll -> discovered game window
```

The `TCLS_CORE_WND_%u` suffix source is the object field pushed at
`0x18F54`; no proof was found that this `%u` is a PID.  The safe conclusion
is a host-generated numeric window identity, with the final semantic name
left `UNKNOWN`.

## Phase 7 - TenProxy as the Game-Side Endpoint

Recovered edge:

```text
CTclsProxy::Initialize
    -> GetCurrentProcessId
    -> build TCLS_SHAREDMEMEMORY<pid>
    -> OpenFileMappingW
    -> MapViewOfFile
    -> mapped context
```

The mapping is opened read-only (`0xF001F`) and copied into the proxy object
at `0x6273` onward.  The TenProxy numeric message path is separate:

```text
CTclsProxy::NotifyExit
    -> window discovery
    -> PostMessageW(0xBD0, 0, 0)
```

## Phase 8 - Bidirectional Protocol

```text
          tcls_core.exe / TCLSHostApp
                 |
      TCLS_SHAREDMEMEMORY<game PID>
                 |
                 v
            TenProxy.dll
                 |
         numeric window messages
                 |
                 v
          TCLS core window
```

Edge classifications:

```text
producer name construction            STATIC_DATAFLOW_CONFIRMED
producer open/create                   STATIC_CONFIRMED
game-side OpenFileMappingW             STATIC_CONFIRMED
game-side MapViewOfFile                STATIC_CONFIRMED
window discovery                       STATIC_CONFIRMED
numeric PostMessage                    STATIC_CONFIRMED
exact semantic command table           UNKNOWN
```

## Phase 9 - Native Bootstrap Protocol Entry

Searches covered `codoMP_client_shipRetail.exe`, `Base.dll`, `ClientBase.dll`,
and `TenProxy.dll` for `LoadLibrary`, `GetProcAddress`, constructor
registration, global objects, and `CTclsProxy`.

The available evidence proves the named-object protocol and the TenProxy
endpoint, but not a direct static native-bootstrap-to-TenProxy call.

```text
NATIVE_BOOTSTRAP_TO_TENPROXY = STATIC_BOUNDARY
NATIVE_BOOTSTRAP_TO_TCLS     = STATIC_BOUNDARY
```

## Phase 10 - tcls_core.exe process creation

The host process that starts `tcls_core.exe` is not present with a matching
`CreateProcess` argument in the analysed tree.

```text
TCLS_PROCESS_CREATION = EXTERNAL_HOST_UNAVAILABLE
TCLS_UPSTREAM_CALLER  = STATIC_BOUNDARY
```

This remains a host-process boundary and is not upgraded to a recovered
WeGame caller.

## Final Status

```text
TCLS_OBJECT_MODEL = STATIC_CONFIRMED
TCLS_COMMAND_TABLE = MISIDENTIFIED_VTABLE; PRIMARY VTABLE 0x16A4DC
SUB8D2A2_CALLERS = STATIC_CONFIRMED
SUB8D2A2_ARGUMENTS = STATIC_CONFIRMED (no stack args; ECX=this)

TCLS_CORE_SHARED_MEMORY = STATIC_CONFIRMED
TCLS_CORE_MUTEX = STATIC_CONFIRMED

TCLS_GAME_SHARED_MEMORY = STATIC_CONFIRMED
GAMEPID_SOURCE = STATIC_DATAFLOW_CONFIRMED
GAMEPID_DATAFLOW = STATIC_DATAFLOW_CONFIRMED

TCLS_WINDOW = STATIC_CONFIRMED
TCLS_MESSAGE_PROTOCOL = STATIC_CONFIRMED (numeric PostMessage path)

TENPROXY_PROTOCOL_ENDPOINT = STATIC_CONFIRMED
TENPROXY_TO_TCLS = STATIC_CONFIRMED
TCLS_TO_TENPROXY = STATIC_CONFIRMED (named object)

NATIVE_BOOTSTRAP_TO_TENPROXY = STATIC_BOUNDARY
NATIVE_BOOTSTRAP_TO_TCLS = STATIC_BOUNDARY

TCLS_PROCESS_CREATION = EXTERNAL_HOST_UNAVAILABLE
TCLS_UPSTREAM_CALLER = STATIC_BOUNDARY

STATIC_BOOTSTRAP_LINK = HOST_PROCESS_BOUNDARY
STATIC_BOOTSTRAP_LINK_TYPE = TCLS_HOST_UNRESOLVED + PID-NAMED-SHARED-MEMORY
                             + WINDOW-MESSAGE IPC

RUNTIME_GETRESOURCE_CALL = UNKNOWN
RUNTIME_INITINGAMEAPP = UNKNOWN
RUNTIME_IFS2_LOAD = UNKNOWN
RUNTIME_CREATEIFS = UNKNOWN
RUNTIME_FIRST_FAILURE = UNKNOWN
```

## Remaining Unknowns

```text
U01  The exact game-ID-to-repair-path semantics of 0x11, 0x18, and 0x63.
U02  The complete downstream storage/caller chain of GetRealGamePID.
U03  Whether TCLS_CORE_WND_%u's %u is host PID, process identity, or another
     numeric context value.
U04  The exact message semantics of 0xBD0 and 0x8889 beyond their call sites.
U05  The binary that starts tcls_core.exe; no matching external host module is
     present in this workspace.
U06  The exact native bootstrap path that loads/initializes TenProxy.dll.
```
