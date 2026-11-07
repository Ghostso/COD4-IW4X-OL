#!/usr/bin/env python3
"""Generate the EX-067 static-analysis report and evidence artifacts.

All target bytes are read-only.  The script emits only text/CSV artifacts in
the repository root.
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
        "ex067_shared_memory_objects.csv",
        [
            "object",
            "producer_module",
            "producer_site",
            "consumer_module",
            "consumer_site",
            "size",
            "protection",
            "security",
            "role",
            "evidence",
        ],
        [
            {
                "object": "TCLS_SHAREDMEMEMORY<decimal game PID>",
                "producer_module": "tcls_core.exe",
                "producer_site": "0x798E/0x799E -> sub_7D10; 0x40B9/0x40C9 -> sub_7D10",
                "consumer_module": "TenProxy.dll",
                "consumer_site": "0x6176/0x619B/0x61C7 -> 0x61E2 OpenFileMappingW; 0x6273 MapViewOfFile",
                "size": "0x80000 (512 KiB)",
                "protection": "PAGE_READWRITE (4) for producer; FILE_MAP_ALL_ACCESS (0xF001F) for both",
                "security": "InitializeSecurityDescriptor + SetSecurityDescriptorDacl(NULL DACL)",
                "role": "game-PID keyed tag container consumed by TenProxy",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "object": "RAIL_TCLS_SHARED<LUID decimal>",
                "producer_module": "tcls_core.exe",
                "producer_site": "0x794B-0x796A -> sub_7D10",
                "consumer_module": "not recovered in the analysed TCLS/TenProxy edge",
                "consumer_site": "",
                "size": "0x80000 (512 KiB)",
                "protection": "PAGE_READWRITE through sub_7D10",
                "security": "same null-DACL producer helper",
                "role": "separate RAIL context, not the TenProxy mapping",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "object": "TCLS_CORE_SHARE_MEMORY_<suffix>",
                "producer_module": "tcls_core.exe",
                "producer_site": "name builder sub_4077F0; mapping callers include 0x7D81/0x7ED1/0xC4F7",
                "consumer_module": "TCLSHostApp / TCLS core",
                "consumer_site": "named core protocol",
                "size": "per caller; not the game-PID mapping",
                "protection": "recovered per caller",
                "security": "recovered per caller",
                "role": "TCLS host shared-memory namespace",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "object": "TCLS_SHELLMEMORY_<context>",
                "producer_module": "TCLS.dll",
                "producer_site": "CreateFileMappingW 0x3F67A; MapViewOfFile 0x3F789",
                "consumer_module": "TCLS launcher/UI shell",
                "consumer_site": "mapped shell context",
                "size": "caller-defined",
                "protection": "caller-defined",
                "security": "caller-defined",
                "role": "launcher/UI shell context",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "object": "TCLS_TASMEMORY_<context>",
                "producer_module": "TCLS.dll",
                "producer_site": "name builder 0x3C2DF0 vicinity",
                "consumer_module": "TAS path",
                "consumer_site": "mapped context",
                "size": "not recovered",
                "protection": "not recovered",
                "security": "not recovered",
                "role": "TAS context",
                "evidence": "STATIC_CONFIRMED",
            },
        ],
    )

    mapped_fields = [
        ("+0x00", "4", "read", "tcls_core sub_7D10", "TenProxy 0x62E9", "mapped memory version = 0x40", "STATIC_DATAFLOW_CONFIRMED"),
        ("+0x04", "tag_count*4", "read", "tcls_core sub_7D10", "TenProxy +0x18C8", "tag offset table base", "STATIC_DATAFLOW_CONFIRMED"),
        ("+0x04+4*(tag-1)", "4", "read", "host tag writer", "TenProxy GetInt/GetDWORD/GetString/GetBYTE", "offset of tag entry relative to mapped base", "STATIC_DATAFLOW_CONFIRMED"),
        ("entry+0x00", "4", "read", "host tag writer", "TenProxy 0x7CFC/0x7DFC/0x81A0/0x82EC", "entry length/type tag", "STATIC_DATAFLOW_CONFIRMED"),
        ("entry+0x04", "entry_length", "read", "host tag writer", "TenProxy accessor data", "entry payload", "STATIC_DATAFLOW_CONFIRMED"),
        ("tag 0x13 -> entry", "entry_length", "read", "host tag writer", "TenProxy 0x638C/0x6392", "schema root; [tag0x13 entry+0x4C] points to nested table", "STATIC_CONFIRMED"),
        ("tag 0x35 entry", "entry_length", "read", "host tag writer", "TenProxy 0x82B7 -> 0x1000D15C", "nested GameServer records", "STATIC_REACHABLE"),
        ("tag 0x0F", "wide string", "read", "host tag writer", "TenProxy 0x63CD", "window/context string target buffer", "STATIC_REACHABLE"),
        ("tag 0x0E", "wide string", "read", "host tag writer", "TenProxy 0x6440", "login/context string", "STATIC_REACHABLE"),
        ("tag 0x05", "16 bytes", "read", "host tag writer", "TenProxy 0x64C7", "string/signature material", "STATIC_REACHABLE"),
        ("tag 0x03", "1 byte", "read", "host tag writer", "TenProxy 0x653F", "string/signature material", "STATIC_REACHABLE"),
        ("tag 0x04", "0x80 bytes", "read", "host tag writer", "TenProxy 0x65A6", "GameSignature payload", "STATIC_DATAFLOW_CONFIRMED"),
        ("tag 0x1A", "1 byte", "read", "host tag writer", "TenProxy 0x664F", "JumpSignature length/selector", "STATIC_REACHABLE"),
        ("tag 0x1B", "0x70 bytes", "read", "host tag writer", "TenProxy 0x66B6", "JumpSignature payload", "STATIC_DATAFLOW_CONFIRMED"),
        ("tag 0x10", "0x28 bytes", "read", "host tag writer", "TenProxy 0x6783", "PASS/result structure", "STATIC_REACHABLE"),
        ("tag 0x35 nested data", "0x210 bytes per record", "read", "host tag writer", "TenProxy 0x703A-0x724C", "GameServer records", "STATIC_REACHABLE"),
    ]
    proxy_fields = [
        ("+0x18C4", "4", "write", "TenProxy Initialize", "TenProxy mapped accessors", "mapped_base", "STATIC_CONFIRMED"),
        ("+0x18C8", "4", "write", "TenProxy Initialize", "TenProxy mapped accessors", "mapped_base + 4, offset table", "STATIC_CONFIRMED"),
        ("+0x18CC", "4", "write", "TenProxy Initialize", "TenProxy nested accessors", "mapped_base + tag[0x13] entry offset", "STATIC_CONFIRMED"),
        ("+0x18D0", "4", "write/read", "TenProxy Initialize", "TenProxy Initialize version check", "mapped header version", "STATIC_CONFIRMED"),
        ("+0x18D4", "4", "write/read", "TenProxy OpenFileMappingW", "TenProxy MapViewOfFile/CloseHandle", "mapping handle", "STATIC_CONFIRMED"),
        ("+0x18E0", "4", "write", "TenProxy Initialize success", "TenProxy state users", "initialized flag", "STATIC_CONFIRMED"),
        ("+0x8AC", "4", "write", "TenProxy GetGameSignature path", "TenProxy callers", "GameSignature length/state", "STATIC_CONFIRMED"),
        ("+0x8B0", "0x404", "write", "TenProxy Initialize", "TenProxy GetGameSignature path", "GameSignature buffer", "STATIC_CONFIRMED"),
        ("+0xCB4", "0x384", "write", "TenProxy Initialize", "TenProxy JumpSignature path", "JumpSignature buffer", "STATIC_CONFIRMED"),
    ]
    rows: list[dict[str, str]] = []
    for offset, size, rw, producer, consumer, semantic, evidence in mapped_fields + proxy_fields:
        rows.append(
            {
                "offset": offset,
                "size": size,
                "read_write": rw,
                "producer": producer,
                "consumer": consumer,
                "semantic_candidate": semantic,
                "evidence": evidence,
            }
        )
    write_csv(
        "ex067_shared_memory_fields.csv",
        ["offset", "size", "read_write", "producer", "consumer", "semantic_candidate", "evidence"],
        rows,
    )

    write_csv(
        "ex067_shared_memory_producer.csv",
        [
            "module",
            "function",
            "site",
            "operation",
            "mapping_name_source",
            "size",
            "write_or_publish",
            "evidence",
        ],
        [
            {
                "module": "tcls_core.exe",
                "function": "sub_4077F0 name builder",
                "site": "0x798B-0x799E",
                "operation": "format TCLS_SHAREDMEMEMORY + decimal PID",
                "mapping_name_source": "[ebp+0xC] at 0x798B",
                "size": "",
                "write_or_publish": "no mapping write; name passed to sub_7D10",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "module": "tcls_core.exe",
                "function": "sub_4077F0 name builder",
                "site": "0x40B6-0x40C9",
                "operation": "same name construction in second caller family",
                "mapping_name_source": "[ebp+0xC] at 0x40B6",
                "size": "",
                "write_or_publish": "no mapping write; name passed to sub_7D10",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "module": "tcls_core.exe",
                "function": "sub_7D10",
                "site": "0x7D47/0x7D57/0x7D81",
                "operation": "InitializeSecurityDescriptor, SetSecurityDescriptorDacl(NULL), CreateFileMappingW",
                "mapping_name_source": "lpName argument",
                "size": "0x80000",
                "write_or_publish": "creates mapping handle",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "module": "tcls_core.exe",
                "function": "sub_7D10",
                "site": "0x7D9A",
                "operation": "MapViewOfFile(FILE_MAP_ALL_ACCESS)",
                "mapping_name_source": "handle from CreateFileMappingW",
                "size": "0x80000",
                "write_or_publish": "view installed in producer object",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "module": "tcls_core.exe",
                "function": "sub_7D10",
                "site": "0x7DD3",
                "operation": "write version 0x40 at view+0x00",
                "mapping_name_source": "mapped view",
                "size": "4",
                "write_or_publish": "initial header publish",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "module": "tcls_core.exe",
                "function": "sub_7D10",
                "site": "0x7DDB-0x7DEC",
                "operation": "initialize relative pointers at view+0x04/+0x08/+0x0C",
                "mapping_name_source": "mapped view",
                "size": "12",
                "write_or_publish": "initial tag-container wrapper publish",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "module": "tcls_core.exe",
                "function": "sub_7830/sub_3DC5",
                "site": "0x78A0/0x3DC5 and callers",
                "operation": "second mapping RAIL_TCLS_SHARED<LUID> uses same sub_7D10 helper",
                "mapping_name_source": "AllocateLocallyUniqueId -> sprintf %s%llu",
                "size": "0x80000",
                "write_or_publish": "separate mapping; do not merge with TCLS_SHAREDMEMEMORY",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
        ],
    )

    write_csv(
        "ex067_gamepid_dataflow.csv",
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
                "stage": "mapping-name PID producer argument",
                "module": "tcls_core.exe",
                "function": "sub_798E",
                "site": "0x798B",
                "source": "game PID argument [ebp+0xC]",
                "destination": "sprintf TCLS_SHAREDMEMEMORY + %lu",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "mapping-name PID producer argument",
                "module": "tcls_core.exe",
                "function": "sub_40B9",
                "site": "0x40B6",
                "source": "game PID argument [ebp+0xC]",
                "destination": "sprintf TCLS_SHAREDMEMEMORY + %lu",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "mapping-name consumer PID",
                "module": "TenProxy.dll",
                "function": "CTclsProxy::Initialize",
                "site": "0x60EF",
                "source": "GetCurrentProcessId",
                "destination": "decimal suffix at 0x6157",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "mapping-name consumer PID",
                "module": "TenProxy.dll",
                "function": "CTclsProxy::Initialize",
                "site": "0x6176-0x61C7",
                "source": "decimal PID",
                "destination": "OpenFileMappingW name",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "payload PID",
                "module": "TCLS_SHAREDMEMEMORY payload",
                "function": "",
                "site": "recovered tag accesses",
                "source": "UNKNOWN",
                "destination": "no static write of PID into a named tag was recovered",
                "evidence": "UNKNOWN",
            },
            {
                "stage": "RealGamePID reader",
                "module": "TCLS.dll",
                "function": "Clauncher::GetRealGamePID",
                "site": "OpenFileMapping/MapViewOfFile path near GetRealGamePID string xrefs",
                "source": "mapped structure",
                "destination": "returned PID",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "stage": "window PID discovery",
                "module": "TCLS.dll",
                "function": "sub_8721A",
                "site": "0x88C21/0x88CEC/0x88D84",
                "source": "FindWindowW + GetWindowThreadProcessId + OpenProcess",
                "destination": "process termination/notification",
                "evidence": "STATIC_CONFIRMED",
            },
        ],
    )

    write_csv(
        "ex067_gameid_dataflow.csv",
        [
            "stage",
            "module",
            "function",
            "site",
            "source",
            "destination",
            "semantic",
            "evidence",
        ],
        [
            {
                "stage": "constructor",
                "module": "tcls_core.exe",
                "function": "sub_89EEE",
                "site": "0x89F72/0x89F75, 0x89FE2/0x89FE8",
                "source": "zeroed 64-bit temporary",
                "destination": "[this+0x30]/[this+0x34] = 0",
                "semantic": "initial GameID",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "stage": "Init",
                "module": "tcls_core.exe",
                "function": "sub_8A134",
                "site": "0x8A1B3/0x8A1B9",
                "source": "zeroed 64-bit temporary",
                "destination": "[this+0x30]/[this+0x34] = 0",
                "semantic": "GameID reset on initialization",
                "evidence": "STATIC_CONFIRMED",
            },
            {
                "stage": "Update write",
                "module": "tcls_core.exe",
                "function": "sub_8A290",
                "site": "0x8A340/0x8A346",
                "source": "arg3 [ebp+0xC] and arg4 [ebp+0x10]",
                "destination": "[this+0x30]/[this+0x34]",
                "semantic": "64-bit GameID",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "logging",
                "module": "tcls_core.exe",
                "function": "sub_8C6D8",
                "site": "0x8C71D/0x8C720",
                "source": "[this+0x30]/[this+0x34]",
                "destination": "gameID: %llu diagnostic",
                "semantic": "64-bit decimal GameID",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "game branch",
                "module": "tcls_core.exe",
                "function": "sub_8DBEB",
                "site": "0x8DC49/0x8DC96/0x8DCBD",
                "source": "[this+0x30]/[this+0x34]",
                "destination": "compare low dword with 0x63, 0x18, 0x11",
                "semantic": "game-specific update/repair branch; not command ID",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "IIPS selection",
                "module": "tcls_core.exe",
                "function": "sub_8C783 -> sub_8C8CF",
                "site": "0x8C7B6-0x8C7C6; [this+0x30/+0x34] passed as GameID context",
                "source": "[this+0x30]/[this+0x34]",
                "destination": "IIPS config/plugin context",
                "semantic": "GameID selects IIPS path/config",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "IIPS creation",
                "module": "tcls_core.exe",
                "function": "sub_8D2A2",
                "site": "0x8D2D4-0x8D2E4; 0x8D353/0x8D38A/0x8D39F",
                "source": "[this+0x30]/[this+0x34]",
                "destination": "LoadLibraryW/CreateIIPSRepair call context",
                "semantic": "same 64-bit GameID feeds IIPS repair selection",
                "evidence": "STATIC_DATAFLOW_CONFIRMED",
            },
            {
                "stage": "PID relation",
                "module": "TCLS vs tcls_core",
                "function": "",
                "site": "",
                "source": "GamePID and GameID",
                "destination": "no arithmetic or copy relation recovered",
                "semantic": "distinct identifiers",
                "evidence": "STATIC_BOUNDARY",
            },
        ],
    )

    write_csv(
        "ex067_tenproxy_init.csv",
        [
            "stage",
            "function",
            "site",
            "operation",
            "destination",
            "evidence",
        ],
        [
            {"stage": "export", "function": "Invoke", "site": "0x13E3 -> 0x1D70", "operation": "exported dispatcher accepts command 0x566", "destination": "allocates 0x18E4-byte object", "evidence": "STATIC_CONFIRMED"},
            {"stage": "constructor", "function": "sub_13A2 -> 0x5510", "site": "0x5510-0x56D6", "operation": "construct CTclsProxy object and vtables", "destination": "object fields initialized", "evidence": "STATIC_CONFIRMED"},
            {"stage": "initialize", "function": "sub_5E4A", "site": "0x5E4A-0x6887", "operation": "CTclsProxy::Initialize body", "destination": "mapped payload/tag context", "evidence": "STATIC_CONFIRMED"},
            {"stage": "PID", "function": "sub_5E4A", "site": "0x60EF", "operation": "GetCurrentProcessId", "destination": "name suffix", "evidence": "STATIC_DATAFLOW_CONFIRMED"},
            {"stage": "open", "function": "sub_5E4A", "site": "0x61E2", "operation": "OpenFileMappingW(FILE_MAP_ALL_ACCESS)", "destination": "[object+0x18D4]", "evidence": "STATIC_CONFIRMED"},
            {"stage": "map", "function": "sub_5E4A", "site": "0x6273", "operation": "MapViewOfFile", "destination": "temporary mapped base [ebp-0xC8C]", "evidence": "STATIC_CONFIRMED"},
            {"stage": "version", "function": "sub_5E4A", "site": "0x62E9-0x62EB", "operation": "read mapped_base[0]", "destination": "[object+0x18D0]", "evidence": "STATIC_DATAFLOW_CONFIRMED"},
            {"stage": "schema", "function": "sub_5E4A", "site": "0x636B-0x6383", "operation": "store mapped base and mapped base+4 offset table", "destination": "[object+0x18C4]/[object+0x18C8]", "evidence": "STATIC_DATAFLOW_CONFIRMED"},
            {"stage": "nested schema", "function": "sub_5E4A", "site": "0x638C-0x6392", "operation": "read tag 0x13 entry offset at table+0x4C", "destination": "[object+0x18CC]", "evidence": "STATIC_DATAFLOW_CONFIRMED"},
            {"stage": "fields", "function": "sub_5E4A", "site": "0x64B3-0x6822", "operation": "read GameSignature, JumpSignature and PASS tags into object buffers", "destination": "object+0x8AC/+0x8B0/+0xCB4 and state", "evidence": "STATIC_DATAFLOW_CONFIRMED"},
            {"stage": "complete", "function": "sub_5E4A", "site": "0x6822", "operation": "set initialized flag", "destination": "[object+0x18E0]=1", "evidence": "STATIC_CONFIRMED"},
            {"stage": "upstream", "function": "Invoke", "site": "0x1D70/0x9EA4/0x9F0D", "operation": "command dispatch creates proxy object; no CRT/TLS/DllMain automatic Initialize recovered", "destination": "external/bootstrap call boundary", "evidence": "STATIC_BOUNDARY"},
        ],
    )

    write_csv(
        "ex067_native_tenproxy_edges.csv",
        [
            "edge",
            "source",
            "target",
            "site",
            "classification",
            "detail",
        ],
        [
            {"edge": "native bootstrap -> TenProxy loading", "source": "codoMP_client_shipRetail.exe", "target": "TenProxy.dll", "site": "no static LoadLibrary/GetProcAddress call site recovered", "classification": "STATIC_BOUNDARY", "detail": "The native image's statically parsed import call edges do not include TenProxy or loader resolution."},
            {"edge": "native bootstrap -> TenProxy entry", "source": "codoMP_client_shipRetail.exe", "target": "TenProxy.dll!Invoke", "site": "TenProxy export 0x13E3; command 0x566 at 0x1D8E", "classification": "STATIC_BOUNDARY", "detail": "The only recovered endpoint is the exported Invoke dispatcher; the caller binary is outside the recovered native image chain."},
            {"edge": "TenProxy -> TCLS_SHAREDMEMEMORY", "source": "TenProxy.dll", "target": "TCLS_SHAREDMEMEMORY<game PID>", "site": "0x60EF/0x61E2/0x6273", "classification": "STATIC_DATAFLOW_CONFIRMED", "detail": "GetCurrentProcessId directly builds the object-name suffix."},
            {"edge": "TCLS_SHAREDMEMEMORY -> TenProxy", "source": "tcls_core.exe", "target": "TenProxy.dll", "site": "0x798E/0x799E/0x7D10 and TenProxy 0x61E2", "classification": "STATIC_DATAFLOW_CONFIRMED", "detail": "Named-object protocol connects the two processes without a direct code edge."},
            {"edge": "Base.dll -> TenProxy", "source": "Base.dll", "target": "TenProxy.dll", "site": "TCLS_SHAREDMEMEMORY literals at 0x88FFFC/0x890108", "classification": "STATIC_BOUNDARY", "detail": "Literal presence is not a recovered direct dependency or call."},
            {"edge": "ClientBase.dll -> TenProxy", "source": "ClientBase.dll", "target": "TenProxy.dll", "site": "TCLS_SHAREDMEMEMORY literals at 0x1D5000/0x1D508C", "classification": "STATIC_BOUNDARY", "detail": "Literal presence indicates protocol participation; no direct TenProxy call/import was recovered."},
            {"edge": "native bootstrap -> TCLS host process", "source": "CODOL native image", "target": "tcls_core.exe", "site": "outside available static graph", "classification": "STATIC_BOUNDARY", "detail": "No matching CreateProcess(tcls_core.exe) caller is present in the analysed tree."},
        ],
    )

    write_csv(
        "ex067_window_protocol.csv",
        [
            "direction",
            "sender",
            "receiver",
            "message_id",
            "payload",
            "semantic",
            "evidence",
        ],
        [
            {"direction": "TenProxy -> TCLS core", "sender": "TenProxy.dll", "receiver": "TCLS_CORE_WND window", "message_id": "0xBD0", "payload": "wParam=0 lParam=0", "semantic": "TCLS_GMAE_EXIT log label near call site", "evidence": "STATIC_CONFIRMED"},
            {"direction": "TCLS.dll -> game window", "sender": "TCLS.dll", "receiver": "found game window", "message_id": "0x8889", "payload": "wParam=0 lParam=0", "semantic": "termination/notification path", "evidence": "STATIC_CONFIRMED"},
            {"direction": "TenProxy -> TCLS core", "sender": "TenProxy.dll", "receiver": "unknown/discovered window", "message_id": "UNKNOWN", "payload": "TCLS_TENPROXY_RESULT is a diagnostic label, not a registered message string", "semantic": "numeric ID not recovered in this pass", "evidence": "STATIC_BOUNDARY"},
            {"direction": "TCLS core -> TenProxy", "sender": "TCLS core", "receiver": "TenProxy", "message_id": "UNKNOWN", "payload": "named shared memory plus tag protocol", "semantic": "data transport, not a window-message direction", "evidence": "STATIC_DATAFLOW_CONFIRMED"},
        ],
    )

    write_csv(
        "ex067_historical_crosscheck.csv",
        [
            "source",
            "observed",
            "classification",
            "crosscheck",
            "limits",
        ],
        [
            {"source": "COD OL/TenproxyLog/20201216_215111.log", "observed": "GetCurrentProcessId = 4540", "classification": "HISTORICAL_DYNAMIC", "crosscheck": "matches static TenProxy 0x60EF -> name suffix dataflow", "limits": "not current runtime evidence"},
            {"source": "COD OL/TenproxyLog/20201216_215111.log", "observed": "OpenFileMapping TCLS_SHAREDMEMEMORY+4540 Success!", "classification": "HISTORICAL_DYNAMIC", "crosscheck": "matches static mapping name construction at tcls_core 0x798E/0x40B9", "limits": "does not prove current mapping exists"},
            {"source": "COD OL/TenproxyLog/20201216_215111.log", "observed": "MapViewOfFile Success!", "classification": "HISTORICAL_DYNAMIC", "crosscheck": "matches static TenProxy 0x6273", "limits": "no current-runtime confirmation"},
            {"source": "COD OL/TenproxyLog/20201216_215111.log", "observed": "GetGameSignatrue Success!", "classification": "HISTORICAL_DYNAMIC", "crosscheck": "matches static tag 0x04 -> GameSignature buffer path", "limits": "historical log is not a runtime claim"},
            {"source": "COD OL/TenproxyLog/20201216_215111.log", "observed": "TenPostMessage Post TCLS_TENPROXY_RESULT Message Success!", "classification": "HISTORICAL_DYNAMIC", "crosscheck": "TenProxy contains the label; exact numeric message ID not recovered", "limits": "no static numeric message proof"},
        ],
    )

    report = """# CODOL_EX067_TCLS_SHARED_MEMORY_LAYOUT

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
"""
    (ROOT / "CODOL_EX067_TCLS_SHARED_MEMORY_LAYOUT.md").write_text(
        report, encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
