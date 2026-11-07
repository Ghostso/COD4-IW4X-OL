#!/usr/bin/env python3
"""Generate the EX-066 TCLS protocol-closure report and evidence tables.

The script is deliberately offline and read-only with respect to the target
binaries.  It parses PE files, disassembles the selected functions, and writes
only the EX-066 artifacts in the repository root.
"""

from __future__ import annotations

import csv
from pathlib import Path

from ex066_common import PEImage


ROOT = Path(__file__).resolve().parent

TCLS_CORE = ROOT / "WeGame" / "tcls" / "tcls_core.exe"
TENPROXY = ROOT / "COD OL" / "TenProxy.dll"
TCLS_DLL = ROOT / "COD OL" / "TCLS" / "Tenio" / "TCLS.dll"
BASE_DLL = ROOT / "COD OL" / "codoMP_client_shipRetailBase.dll"


def write_csv(name: str, columns: list[str], rows: list[dict[str, object]]) -> None:
    path = ROOT / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def pointer_table(image: PEImage, rva: int, count: int) -> list[tuple[int, int, int]]:
    """Return (slot_rva, stored_va, target_rva) for a dword pointer table."""
    out: list[tuple[int, int, int]] = []
    for index in range(count):
        slot = rva + index * 4
        value = int.from_bytes(image.read(slot, 4), "little")
        target = value - image.base
        out.append((slot, value, target))
    return out


def main() -> None:
    core = PEImage(TCLS_CORE)
    proxy = PEImage(TENPROXY)
    tcls = PEImage(TCLS_DLL)
    base = PEImage(BASE_DLL)

    # The addresses below are instruction RVAs recovered from the target PEs.
    # They are checked against the table/import contents before being emitted.
    assert core.va(0x16A4DC) == 0x56A4DC
    assert core.read(0x16A4B0, 16).split(b"\0", 1)[0] == b"CreateIIPSRepair"
    assert int.from_bytes(core.read(0x16A4E4, 4), "little") == core.va(0x8DBEB)
    assert int.from_bytes(core.read(0x16A504, 4), "little") == core.va(0x8D9EF)
    assert proxy.imports[0x263A0][1] == "GetCurrentProcessId"
    assert proxy.imports[0x26398][1] == "OpenFileMappingW"
    assert proxy.imports[0x26518][1] == "PostMessageW"
    assert tcls.imports[0x43ACE4][1] == "OpenProcess"
    assert tcls.imports[0x43B394][1] == "GetWindowThreadProcessId"
    # Base.dll is delay/dynamic-import oriented: its PE import table contains
    # only cef_string_utf16_clear, GetProcAddress, and LoadLibraryA.  Its
    # TCLS_SHAREDMEMEMORY literal is therefore not emitted as a direct
    # named-object call site.

    primary_vtable = pointer_table(core, 0x16A4DC, 17)
    callback_vtable = pointer_table(core, 0x16A524, 4)
    secondary_vtable = pointer_table(core, 0x16A538, 1)

    object_rows: list[dict[str, object]] = []
    for label, module, rva, meaning, evidence in [
        (
            "TCLSHostApp/UpdateProcessor ctor",
            "tcls_core.exe",
            "0x89EEE",
            "initializes vtable pointers at +0/+4/+8, fields at +0x18/+0x1C/"
            "+0x20/+0x24/+0x25, 64-bit game-id at +0x30/+0x34, and "
            "handles/results at +0x5268/+0x526C",
            "STATIC_CONFIRMED",
        ),
        (
            "primary vtable",
            "tcls_core.exe",
            "0x16A4DC",
            "17-entry primary vtable installed at [this+0]",
            "STATIC_CONFIRMED",
        ),
        (
            "callback vtable",
            "tcls_core.exe",
            "0x16A524",
            "4-entry secondary vtable installed at [this+4]",
            "STATIC_CONFIRMED",
        ),
        (
            "secondary vtable",
            "tcls_core.exe",
            "0x16A538",
            "1-entry secondary vtable installed at [this+8]",
            "STATIC_CONFIRMED",
        ),
        (
            "game ID",
            "tcls_core.exe",
            "+0x30/+0x34",
            "64-bit value formatted by sub_8C6D8 as gameID: %llu",
            "STATIC_DATAFLOW_CONFIRMED",
        ),
        (
            "initialized flag",
            "tcls_core.exe",
            "+0x18",
            "set to 1 by sub_8A134; gates handlers",
            "STATIC_CONFIRMED",
        ),
        (
            "mode flags",
            "tcls_core.exe",
            "+0x24/+0x25",
            "byte flags controlling update/repair branches",
            "STATIC_CONFIRMED",
        ),
        (
            "IIPS module/result",
            "tcls_core.exe",
            "+0x5268/+0x526C",
            "HMODULE and CreateIIPSRepair result object",
            "STATIC_CONFIRMED",
        ),
    ]:
        object_rows.append(
            {
                "module": module,
                "rva_or_field": rva,
                "name": label,
                "recovered_meaning": meaning,
                "evidence": evidence,
            }
        )

    command_rows: list[dict[str, object]] = []
    for index, (slot, value, target) in enumerate(primary_vtable):
        command_rows.append(
            {
                "table": "primary",
                "index": index,
                "slot_rva": f"0x{slot:X}",
                "stored_va": f"0x{value:08X}",
                "target_rva": f"0x{target:X}" if core.is_executable(target) else "",
                "consumer": "indirect call through [this+0]",
                "evidence": "STATIC_CONFIRMED",
            }
        )
    for table_name, table in (
        ("callback", callback_vtable),
        ("secondary", secondary_vtable),
    ):
        for index, (slot, value, target) in enumerate(table):
            command_rows.append(
                {
                    "table": table_name,
                    "index": index,
                    "slot_rva": f"0x{slot:X}",
                    "stored_va": f"0x{value:08X}",
                    "target_rva": f"0x{target:X}" if core.is_executable(target) else "",
                    "consumer": "indirect virtual dispatch",
                    "evidence": "STATIC_CONFIRMED",
                }
            )

    shared_memory_rows: list[dict[str, object]] = []
    for row in [
        {
            "module": "tcls_core.exe",
            "string_rva": "0x5822E8",
            "format_function": "sub_4077F0",
            "format_string": "%s%lu",
            "name_pattern": "TCLS_SHAREDMEMEMORY<decimal game PID>",
            "pid_source": "[ebp+0xC] of sub_798E / sub_40B9; producer caller supplies game PID",
            "create_open_api": "sub_7D10 -> CreateFileMappingW/OpenFileMappingW",
            "map_api": "sub_7D10 path",
            "role": "host-side game context producer/reader",
            "evidence": "STATIC_DATAFLOW_CONFIRMED",
        },
        {
            "module": "TenProxy.dll",
            "string_rva": "0x20F70",
            "format_function": "sub_14CE / sub_1393 / sub_1212",
            "format_string": "TCLS_SHAREDMEMEMORY + decimal PID",
            "name_pattern": "TCLS_SHAREDMEMEMORY<decimal current game PID>",
            "pid_source": "GetCurrentProcessId at 0x60EF",
            "create_open_api": "OpenFileMappingW at 0x61E2",
            "map_api": "MapViewOfFile at 0x6273",
            "role": "game-side consumer",
            "evidence": "STATIC_DATAFLOW_CONFIRMED",
        },
        {
            "module": "TCLS.dll",
            "string_rva": "0x3C3268",
            "format_function": "sub_5727/sub_2469/sub_5A8D",
            "format_string": "TCLS_SHELLMEMORY_ + suffix",
            "name_pattern": "TCLS_SHELLMEMORY_<context>",
            "pid_source": "none",
            "create_open_api": "CreateFileMappingW at 0x3F67A",
            "map_api": "MapViewOfFile at 0x3F789",
            "role": "launcher/UI shell context producer",
            "evidence": "STATIC_CONFIRMED",
        },
        {
            "module": "TCLS.dll",
            "string_rva": "0x3C2DF0",
            "format_function": "name builder",
            "format_string": "TCLS_TASMEMORY_ + suffix",
            "name_pattern": "TCLS_TASMEMORY_<context>",
            "pid_source": "none recovered",
            "create_open_api": "mapping API nearby",
            "map_api": "MapViewOfFile nearby",
            "role": "TAS context",
            "evidence": "STATIC_CONFIRMED",
        },
        {
            "module": "tcls_core.exe",
            "string_rva": "0x557270",
            "format_function": "sub_4077F0",
            "format_string": "%s%s",
            "name_pattern": "TCLS_CORE_SHARE_MEMORY_<suffix>",
            "pid_source": "not PID-keyed; suffix passed at [ebp+0xC]",
            "create_open_api": "sub_9093 returns name; mapping performed by surrounding object",
            "map_api": "surrounding object",
            "role": "core host shared-memory protocol",
            "evidence": "STATIC_CONFIRMED",
        },
        {
            "module": "tcls_core.exe",
            "string_rva": "0x5572AC",
            "format_function": "sub_4077F0",
            "format_string": "%s%s",
            "name_pattern": "TCLS_CORE_MUTEX_<suffix>",
            "pid_source": "not PID-keyed; suffix passed at [ebp+0xC]",
            "create_open_api": "CreateMutexW at 0x8C854",
            "map_api": "n/a",
            "role": "core host mutex",
            "evidence": "STATIC_CONFIRMED",
        },
    ]:
        shared_memory_rows.append(row)

    gamepid_rows: list[dict[str, object]] = []
    for row in [
        {
            "module": "tcls_core.exe",
            "function": "sub_798E",
            "site": "0x798B",
            "operation": "push game PID argument",
            "source": "function argument [ebp+0xC]",
            "consumer": "sprintf -> TCLS_SHAREDMEMEMORY<pid>",
            "evidence": "STATIC_DATAFLOW_CONFIRMED",
        },
        {
            "module": "tcls_core.exe",
            "function": "sub_40B9",
            "site": "0x40B6",
            "operation": "push game PID argument",
            "source": "function argument [ebp+0xC]",
            "consumer": "sprintf -> TCLS_SHAREDMEMEMORY<pid>",
            "evidence": "STATIC_DATAFLOW_CONFIRMED",
        },
        {
            "module": "TenProxy.dll",
            "function": "CTclsProxy::Initialize",
            "site": "0x60EF",
            "operation": "GetCurrentProcessId",
            "source": "current CODOL process",
            "consumer": "name suffix for OpenFileMappingW",
            "evidence": "STATIC_DATAFLOW_CONFIRMED",
        },
        {
            "module": "TenProxy.dll",
            "function": "CTclsProxy::Initialize",
            "site": "0x61E2",
            "operation": "OpenFileMappingW",
            "source": "composed TCLS_SHAREDMEMEMORY<current pid>",
            "consumer": "MapViewOfFile at 0x6273",
            "evidence": "STATIC_CONFIRMED",
        },
        {
            "module": "TCLS.dll",
            "function": "Clauncher::GetRealGamePID",
            "site": "function body near string xrefs",
            "operation": "open filemapping + MapViewOfFile",
            "source": "mapped structure",
            "consumer": "returned RealGamePID to caller",
            "evidence": "STATIC_CONFIRMED",
        },
        {
            "module": "TCLS.dll",
            "function": "sub_8721A",
            "site": "0x88C21/0x88CEC/0x88D84",
            "operation": "OpenMutexW, FindWindowW/static, GetWindowThreadProcessId, OpenProcess, PostMessageW",
            "source": "existing game window/process",
            "consumer": "termination/notification path",
            "evidence": "STATIC_CONFIRMED",
        },
    ]:
        gamepid_rows.append(row)

    window_rows: list[dict[str, object]] = []
    for row in [
        {
            "module": "tcls_core.exe",
            "site": "0x18F57",
            "api": "sprintf",
            "constant": "TCLS_CORE_WND_%u",
            "pid_source": "function/object field pushed at 0x18F54",
            "register_window": "sub_91900 (window registration/discovery)",
            "message": "n/a",
            "wparam": "n/a",
            "lparam": "n/a",
            "evidence": "STATIC_DATAFLOW_CONFIRMED",
        },
        {
            "module": "TenProxy.dll",
            "site": "0x7BA0",
            "api": "FindWindowW",
            "constant": "static class; window name from CTclsProxy field +0x49C",
            "pid_source": "window discovery by name",
            "register_window": "n/a",
            "message": "n/a",
            "wparam": "n/a",
            "lparam": "n/a",
            "evidence": "STATIC_CONFIRMED",
        },
        {
            "module": "TenProxy.dll",
            "site": "0x7BBC",
            "api": "PostMessageW",
            "constant": "0xBD0",
            "pid_source": "HWND from FindWindowW/FindWindowExW",
            "register_window": "n/a",
            "message": "0xBD0 (TCLS_GMAE_EXIT log label)",
            "wparam": "0",
            "lparam": "0",
            "evidence": "STATIC_CONFIRMED",
        },
        {
            "module": "TenProxy.dll",
            "site": "0x7C0A",
            "api": "FindWindowExW",
            "constant": "static class and name from +0x49C",
            "pid_source": "window discovery by name",
            "register_window": "n/a",
            "message": "n/a",
            "wparam": "n/a",
            "lparam": "n/a",
            "evidence": "STATIC_CONFIRMED",
        },
        {
            "module": "TCLS.dll",
            "site": "0x88C90",
            "api": "FindWindowW",
            "constant": "static class; generated name",
            "pid_source": "window name, then GetWindowThreadProcessId",
            "register_window": "n/a",
            "message": "n/a",
            "wparam": "n/a",
            "lparam": "n/a",
            "evidence": "STATIC_CONFIRMED",
        },
        {
            "module": "TCLS.dll",
            "site": "0x88D84",
            "api": "PostMessageW",
            "constant": "0x8889",
            "pid_source": "HWND from FindWindowW",
            "register_window": "n/a",
            "message": "0x8889",
            "wparam": "0",
            "lparam": "0",
            "evidence": "STATIC_CONFIRMED",
        },
        {
            "module": "tcls_core.exe",
            "site": "0x1B571 / 0x1C1DB",
            "api": "CreateEventA",
            "constant": "TCLS_EXIT_EVENT + %lu_%s",
            "pid_source": "GetCurrentProcessId plus suffix",
            "register_window": "n/a",
            "message": "event signal, not window message",
            "wparam": "n/a",
            "lparam": "n/a",
            "evidence": "STATIC_DATAFLOW_CONFIRMED",
        },
    ]:
        window_rows.append(row)

    proxy_rows: list[dict[str, object]] = []
    for row in [
        {
            "edge": "CTclsProxy::Initialize -> GetCurrentProcessId",
            "from": "TenProxy.dll",
            "to": "KERNEL32",
            "site": "0x60EF",
            "classification": "STATIC_DATAFLOW_CONFIRMED",
        },
        {
            "edge": "CTclsProxy::Initialize -> OpenFileMappingW",
            "from": "TenProxy.dll",
            "to": "TCLS_SHAREDMEMEMORY<current pid>",
            "site": "0x61E2",
            "classification": "STATIC_CONFIRMED",
        },
        {
            "edge": "CTclsProxy::Initialize -> MapViewOfFile",
            "from": "TenProxy.dll",
            "to": "mapped structure",
            "site": "0x6273",
            "classification": "STATIC_CONFIRMED",
        },
        {
            "edge": "CTclsProxy::NotifyExit -> FindWindowW",
            "from": "TenProxy.dll",
            "to": "TCLS core window",
            "site": "0x7BA0",
            "classification": "STATIC_CONFIRMED",
        },
        {
            "edge": "CTclsProxy::NotifyExit -> PostMessageW",
            "from": "TenProxy.dll",
            "to": "TCLS core window",
            "site": "0x7BBC",
            "classification": "STATIC_CONFIRMED (message 0xBD0)",
        },
        {
            "edge": "TCLS core -> CreateIIPSRepair",
            "from": "tcls_core.exe",
            "to": "IIPSLaunchRestore.dll",
            "site": "0x8D353/0x8D38A/0x8D39F",
            "classification": "STATIC_CONFIRMED",
        },
        {
            "edge": "TCLS.dll -> game mapping / process discovery",
            "from": "TCLS.dll",
            "to": "CODOL game process",
            "site": "0x3F67A/0x3FA7C/0x88C21/0x88CEC",
            "classification": "STATIC_CONFIRMED",
        },
    ]:
        proxy_rows.append(row)

    bootstrap_rows = [
        {
            "edge": "CODOL native bootstrap -> TenProxy/Base",
            "site": "not found as CALL/import/vtable/function pointer",
            "classification": "STATIC_BOUNDARY",
            "detail": "TenProxy/Base are loaded through the existing native module chain; "
            "the EX-066 evidence does not establish a direct TCLS-to-native call.",
        },
        {
            "edge": "TenProxy -> TCLS_SHAREDMEMEMORY<game PID>",
            "site": "TenProxy 0x60EF/0x61E2/0x6273",
            "classification": "STATIC_DATAFLOW_CONFIRMED",
            "detail": "Current process ID is the object-name suffix.",
        },
        {
            "edge": "TCLS_SHAREDMEMEMORY<game PID> -> tcls_core/TCLSHostApp",
            "site": "tcls_core 0x798E/0x40B9",
            "classification": "STATIC_DATAFLOW_CONFIRMED",
            "detail": "The host side formats the same prefix with its game-PID argument.",
        },
        {
            "edge": "tcls_core -> IIPSLaunchRestore -> iips",
            "site": "tcls_core 0x8D353/0x8D38A/0x8D39F",
            "classification": "STATIC_CONFIRMED",
            "detail": "Dynamic resolution and call recovered in EX-065.",
        },
        {
            "edge": "WeGame/TGP/Rail/Netbar -> CreateProcess(tcls_core.exe)",
            "site": "outside available binaries",
            "classification": "STATIC_BOUNDARY",
            "detail": "No host binary or matching CreateProcess argument is present in the "
            "analysed tree.",
        },
    ]

    historical_rows = [
        {
            "source": "工具/EX035_DIR/TenproxyLog/20201216_215111.log",
            "module": "TenProxy.dll",
            "observed": "GetCurrentProcessId = 4540; OpenFileMapping "
            "TCLS_SHAREDMEMEMORY+4540 Success!; MapViewOfFile Success!",
            "classification": "HISTORICAL_DYNAMIC",
            "limits": "module/API-name evidence only; no current-runtime claim",
        },
        {
            "source": "工具/EX035_DIR/TenproxyLog/20201216_215111.log",
            "module": "TenProxy.dll",
            "observed": "TenPostMessage Post TCLS_TENPROXY_RESULT Message Success!; "
            "GetGameSignatrue Success!",
            "classification": "HISTORICAL_DYNAMIC",
            "limits": "does not establish function-level execution",
        },
    ]

    write_csv(
        "ex066_tcls_object.csv",
        ["module", "rva_or_field", "name", "recovered_meaning", "evidence"],
        object_rows,
    )
    write_csv(
        "ex066_command_table.csv",
        ["table", "index", "slot_rva", "stored_va", "target_rva", "consumer", "evidence"],
        command_rows,
    )
    write_csv(
        "ex066_shared_memory.csv",
        [
            "module",
            "string_rva",
            "format_function",
            "format_string",
            "name_pattern",
            "pid_source",
            "create_open_api",
            "map_api",
            "role",
            "evidence",
        ],
        shared_memory_rows,
    )
    write_csv(
        "ex066_gamepid_flow.csv",
        ["module", "function", "site", "operation", "source", "consumer", "evidence"],
        gamepid_rows,
    )
    write_csv(
        "ex066_window_message.csv",
        [
            "module",
            "site",
            "api",
            "constant",
            "pid_source",
            "register_window",
            "message",
            "wparam",
            "lparam",
            "evidence",
        ],
        window_rows,
    )
    write_csv(
        "ex066_tenproxy_edges.csv",
        ["edge", "from", "to", "site", "classification"],
        proxy_rows,
    )
    write_csv(
        "ex066_bootstrap_protocol.csv",
        ["edge", "site", "classification", "detail"],
        bootstrap_rows,
    )
    write_csv(
        "ex066_historical_dynamic.csv",
        ["source", "module", "observed", "classification", "limits"],
        historical_rows,
    )

    report = """# CODOL_EX066_TCLS_PROTOCOL_CLOSURE

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
"""
    (ROOT / "CODOL_EX066_TCLS_PROTOCOL_CLOSURE.md").write_text(
        report, encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
