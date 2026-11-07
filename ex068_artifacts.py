#!/usr/bin/env python3
"""Generate EX-068 report and evidence tables.

Static read-only evidence only.  No target execution or modification occurs.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def write_csv(name: str, columns: list[str], rows: list[dict[str, str]]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    write_csv(
        "ex068_tenproxy_callers.csv",
        [
            "module",
            "function",
            "site",
            "operation",
            "target",
            "evidence",
            "detail",
        ],
        [
            {
                "module": "TenProxy.dll",
                "function": "Invoke",
                "site": "0x13E3 -> 0x1D70",
                "operation": "exported dispatcher",
                "target": "command 0x566",
                "evidence": "STATIC_CONFIRMED",
                "detail": "Thin export thunk jumps to 0x1D70; dispatch compares [ebp+8] with 0x566.",
            },
            {
                "module": "TenProxy.dll",
                "function": "sub_1D70",
                "site": "0x1D8E",
                "operation": "compare command",
                "target": "0x566",
                "evidence": "STATIC_CONFIRMED",
                "detail": "cmp dword ptr [ebp+8], 0x566",
            },
            {
                "module": "TenProxy.dll",
                "function": "sub_1D70",
                "site": "0x1D97",
                "operation": "allocate CTclsProxy",
                "target": "0x18E4 bytes",
                "evidence": "STATIC_CONFIRMED",
                "detail": "Command 0x566 allocates the proxy object and enters constructor.",
            },
            {
                "module": "codoMP_client_shipRetailBase.dll",
                "function": "dynamic import descriptor",
                "site": "0x88FA7C-0x88FA98",
                "operation": "GetTSObject / TenProxy.dll / Invoke tuple",
                "target": "TenProxy.dll!Invoke",
                "evidence": "STATIC_REACHABLE",
                "detail": "The game-side base module carries the object name, DLL name, and ordinal string used by its one-entry dynamic import descriptor.",
            },
            {
                "module": "codoMP_client_shipRetail.exe",
                "function": "packed .tp3 stream",
                "site": "0x184F5F/0x184FA0/0x184FB3",
                "operation": "VM byte stream contains TenProxy.dll, Invoke, and push 0x566",
                "target": "TenProxy.dll!Invoke",
                "evidence": "PACKED_UNRESOLVED",
                "detail": "The byte patterns overlap a packed dispatcher and are not accepted as a proved native CALL edge.",
            },
        ],
    )

    write_csv(
        "ex068_tenproxy_dispatch.csv",
        [
            "object",
            "vtable_or_table",
            "slot",
            "target",
            "semantic",
            "evidence",
        ],
        [
            {
                "object": "CTclsProxy",
                "vtable_or_table": "object vtable",
                "slot": "+0x00",
                "target": "constructor family",
                "semantic": "primary dispatch/table",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "object": "export dispatcher",
                "vtable_or_table": "export thunk table",
                "slot": "ordinal 1",
                "target": "Invoke -> 0x1D70",
                "semantic": "only exported entry",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "object": "export dispatcher",
                "vtable_or_table": "command selector",
                "slot": "0x566",
                "target": "allocate 0x18E4 and call sub_13A2",
                "semantic": "CTclsProxy initialization command",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "object": "CTclsProxy mapped access",
                "vtable_or_table": "accessor slots",
                "slot": "+0x24/+0x28/+0x2C/+0x30/+0x34/+0x38",
                "target": "GetInt/GetDWORD/GetString/GetBYTE/GetStruct",
                "semantic": "tag container read helpers",
                "evidence": "STATIC_CONFIRMED",
            },
        ],
    )

    write_csv(
        "ex068_shared_memory_creators.csv",
        [
            "module",
            "function",
            "site",
            "api",
            "object",
            "role",
            "evidence",
        ],
        [
            {
                "module": "tcls_core.exe",
                "function": "sub_7D10",
                "site": "0x7D81",
                "api": "CreateFileMappingW",
                "object": "TCLS_SHAREDMEMEMORY<decimal game PID>",
                "role": "CREATOR/PRODUCER",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "module": "tcls_core.exe",
                "function": "sub_7D10",
                "site": "0x7D9A",
                "api": "MapViewOfFile",
                "object": "TCLS_SHAREDMEMEMORY<decimal game PID>",
                "role": "PRODUCER VIEW",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "module": "TenProxy.dll",
                "function": "CTclsProxy::Initialize",
                "site": "0x61E2",
                "api": "OpenFileMappingW",
                "object": "TCLS_SHAREDMEMEMORY<current process PID>",
                "role": "OPEN/CONSUMER",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "module": "TenProxy.dll",
                "function": "CTclsProxy::Initialize",
                "site": "0x6273",
                "api": "MapViewOfFile",
                "object": "TCLS_SHAREDMEMEMORY<current process PID>",
                "role": "CONSUMER VIEW",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "module": "codoMP_client_shipRetail.exe",
                "function": "",
                "site": "",
                "api": "CreateFileMappingW/OpenFileMappingW",
                "object": "TCLS_SHAREDMEMEMORY",
                "role": "NO CREATOR/OPENER RECOVERED",
                "evidence": "STATIC_BOUNDARY",
            },
        ],
    )

    write_csv(
        "ex068_shared_memory_fields.csv",
        [
            "object_or_mapped_offset",
            "size",
            "read_write",
            "producer",
            "consumer",
            "semantic",
            "evidence",
        ],
        [
            {
                "object_or_mapped_offset": "mapped+0x00",
                "size": "4",
                "read_write": "write/read",
                "producer": "tcls_core.exe sub_7D10",
                "consumer": "TenProxy.dll CTclsProxy::Initialize",
                "semantic": "version/header 0x40",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "object_or_mapped_offset": "mapped+0x04",
                "size": "tag table",
                "read_write": "write/read",
                "producer": "host tag writer",
                "consumer": "TenProxy tag accessors",
                "semantic": "tag offset table",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "object_or_mapped_offset": "entry+0x00",
                "size": "4",
                "read_write": "write/read",
                "producer": "host tag writer",
                "consumer": "TenProxy accessors",
                "semantic": "entry length/type tag",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "object_or_mapped_offset": "entry+0x04",
                "size": "length",
                "read_write": "write/read",
                "producer": "host tag writer",
                "consumer": "TenProxy accessors",
                "semantic": "payload",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "object_or_mapped_offset": "tag 0x04",
                "size": "0x80",
                "read_write": "read",
                "producer": "host tag writer",
                "consumer": "TenProxy GameSignature path",
                "semantic": "GameSignature payload -> object+0x8B0",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "object_or_mapped_offset": "tag 0x1A/0x1B",
                "size": "selector/0x70",
                "read_write": "read",
                "producer": "host tag writer",
                "consumer": "TenProxy JumpSignature path",
                "semantic": "JumpSignature payload -> object+0xCB4",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
        ],
    )

    write_csv(
        "ex068_gameid_source.csv",
        [
            "stage",
            "module",
            "function",
            "site",
            "source",
            "destination",
            "evidence",
        ],
        [
            {
                "stage": "GameID field",
                "module": "tcls_core.exe",
                "function": "sub_8A290",
                "site": "0x8A340/0x8A346",
                "source": "arg3 [ebp+0xC], arg4 [ebp+0x10]",
                "destination": "[this+0x30]/[this+0x34]",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "GameID formatting",
                "module": "tcls_core.exe",
                "function": "sub_8C6D8",
                "site": "0x8C71D/0x8C720",
                "source": "[this+0x30]/[this+0x34]",
                "destination": "gameID: %llu",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "GameID branch",
                "module": "tcls_core.exe",
                "function": "sub_8DBEB",
                "site": "0x8DC49/0x8DC96/0x8DCBD",
                "source": "low dword",
                "destination": "0x63/0x18/0x11 game paths",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "GameID upstream",
                "module": "external host",
                "function": "UNKNOWN",
                "site": "",
                "source": "UNKNOWN",
                "destination": "sub_8A290 arguments",
                "evidence": "STATIC_BOUNDARY",
            },
        ],
    )

    write_csv(
        "ex068_gamesignature_source.csv",
        [
            "stage",
            "module",
            "site",
            "source",
            "destination",
            "evidence",
            "detail",
        ],
        [
            {
                "stage": "consumer read",
                "module": "TenProxy.dll",
                "site": "0x65A6/0x65B0",
                "source": "tag 0x04",
                "destination": "object+0x8B0, length object+0x8AC",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
                "detail": "Exact semantic remains opaque.",
            },
            {
                "stage": "producer",
                "module": "external host",
                "site": "",
                "source": "UNKNOWN",
                "destination": "TCLS shared-memory tag 0x04",
                "evidence": "STATIC_BOUNDARY",
                "detail": "No writer recovered in the analyzed game-side images.",
            },
            {
                "stage": "IIPS usage",
                "module": "IIPSLaunchRestore.dll / iips.dll",
                "site": "",
                "source": "no shared-memory field edge recovered",
                "destination": "",
                "evidence": "STATIC_BOUNDARY",
                "detail": "Do not upgrade string presence to dataflow.",
            },
        ],
    )

    write_csv(
        "ex068_jumpsignature_source.csv",
        [
            "stage",
            "module",
            "site",
            "source",
            "destination",
            "evidence",
            "detail",
        ],
        [
            {
                "stage": "consumer selector",
                "module": "TenProxy.dll",
                "site": "0x6659",
                "source": "tag 0x1A",
                "destination": "JumpSignature state",
                "evidence": "STATIC_REACHABLE",
                "detail": "Selector/header read.",
            },
            {
                "stage": "consumer payload",
                "module": "TenProxy.dll",
                "site": "0x66B6/0x66C0",
                "source": "tag 0x1B",
                "destination": "object+0xCB4",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
                "detail": "Exact semantic remains opaque.",
            },
            {
                "stage": "producer",
                "module": "external host",
                "site": "",
                "source": "UNKNOWN",
                "destination": "TCLS shared-memory tag 0x1A/0x1B",
                "evidence": "STATIC_BOUNDARY",
                "detail": "No writer recovered in the analyzed game-side images.",
            },
        ],
    )

    write_csv(
        "ex068_native_module_edges.csv",
        [
            "source",
            "target",
            "edge",
            "site",
            "evidence",
            "detail",
        ],
        [
            {
                "source": "codoMP_client_shipRetailBase.dll",
                "target": "TenProxy.dll!Invoke",
                "edge": "dynamic import descriptor",
                "site": "0x88FA7C GetTSObject; 0x88FA88 TenProxy.dll; 0x88FA98 Invoke",
                "evidence": "STATIC_REACHABLE",
                "detail": "The base module contains the complete object/DLL/export tuple.",
            },
            {
                "source": "codoMP_client_shipRetailBase.dll",
                "target": "kernel32!LoadLibraryA / GetProcAddress",
                "edge": "dynamic resolver",
                "site": "IAT +0x9F6C40/+0x9F6C44",
                "evidence": "STATIC_CONFIRMED",
                "detail": "One-entry loader imports are present in the base module.",
            },
            {
                "source": "codoMP_client_shipRetail.exe",
                "target": "TenProxy.dll!Invoke",
                "edge": "packed dispatcher candidate",
                "site": "0x184F5F/0x184FA0/0x184FB3",
                "evidence": "PACKED_UNRESOLVED",
                "detail": "Packed stream contains the string/call template but is not accepted as a direct call edge.",
            },
            {
                "source": "codoMP_client_shipRetail.exe",
                "target": "tcls_core.exe",
                "edge": "process creation",
                "site": "",
                "evidence": "STATIC_BOUNDARY",
                "detail": "No matching CreateProcess caller in the analyzed tree.",
            },
        ],
    )

    write_csv(
        "ex068_iips_protocol_edges.csv",
        [
            "source",
            "target",
            "field",
            "site",
            "evidence",
            "detail",
        ],
        [
            {
                "source": "GameSignature",
                "target": "IIPS",
                "field": "opaque tag blob",
                "site": "",
                "evidence": "STATIC_BOUNDARY",
                "detail": "No shared-memory-to-IIPS argument dataflow recovered.",
            },
            {
                "source": "JumpSignature",
                "target": "IIPS",
                "field": "opaque tag blob",
                "site": "",
                "evidence": "STATIC_BOUNDARY",
                "detail": "No shared-memory-to-IIPS argument dataflow recovered.",
            },
            {
                "source": "GameID",
                "target": "IIPS",
                "field": "64-bit game identifier",
                "site": "tcls_core sub_8C783/sub_8D2A2",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
                "detail": "GameID is passed into IIPS configuration/CreateIIPSRepair context.",
            },
            {
                "source": "TCLS shared memory",
                "target": "IIPSLaunchRestore.dll / iips.dll",
                "field": "tag payload",
                "site": "",
                "evidence": "STATIC_BOUNDARY",
                "detail": "No direct read/dataflow edge recovered.",
            },
        ],
    )

    write_csv(
        "ex068_bootstrap_boundary.csv",
        [
            "edge",
            "source",
            "target",
            "boundary",
            "evidence",
            "detail",
        ],
        [
            {
                "edge": "native bootstrap -> TenProxy",
                "source": "codoMP_client_shipRetail.exe / Base.dll",
                "target": "TenProxy.dll!Invoke(0x566)",
                "boundary": "BASE_DYNAMIC_IMPORT_DESCRIPTOR",
                "evidence": "STATIC_REACHABLE",
                "detail": "Base.dll owns the object/DLL/export tuple; no direct ordinary import from the exe.",
            },
            {
                "edge": "native bootstrap -> TCLS",
                "source": "codoMP_client_shipRetail.exe",
                "target": "tcls_core.exe / TCLS_SHAREDMEMEMORY",
                "boundary": "PACKED_DISPATCHER / EXTERNAL_HOST",
                "evidence": "PACKED_UNRESOLVED",
                "detail": "No proved code or named-object edge from the executable to tcls_core.",
            },
            {
                "edge": "TenProxy -> TCLS",
                "source": "TenProxy.dll",
                "target": "TCLS_SHAREDMEMEMORY<PID>",
                "boundary": "NONE",
                "evidence": "STATIC_CONFIRMED",
                "detail": "GetCurrentProcessId -> OpenFileMappingW -> MapViewOfFile.",
            },
            {
                "edge": "TCLS -> TenProxy",
                "source": "tcls_core.exe",
                "target": "TCLS_SHAREDMEMEMORY<PID>",
                "boundary": "PROCESS_CREATION_EXTERNAL",
                "evidence": "STATIC_CONFIRMED",
                "detail": "Host creates the named object consumed by TenProxy.",
            },
        ],
    )

    report = """# CODOL_EX068_NATIVE_TENPROXY_BRIDGE

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
"""
    (ROOT / "CODOL_EX068_NATIVE_TENPROXY_BRIDGE.md").write_text(
        report, encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
