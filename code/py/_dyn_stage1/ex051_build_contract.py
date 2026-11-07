#!/usr/bin/env python3
"""Build EX-051 Environment Contract artifacts from static iips.dll scan.

Static only. No hooks, no debugger, no VM/TVM0. Reads iips.dll and writes
CSV/JSON/text artifacts under 工具/logs.
"""

from __future__ import annotations

import hashlib
import json
import re
import csv
from pathlib import Path
from datetime import datetime

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32


ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
IIPS = ROOT / r"COD OL\IIPS\iips.dll"
OUTLOG = ROOT / r"工具\logs"


def iat_map(pe):
    mp = {}
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        dll = entry.dll.decode("latin1", "ignore")
        for imp in entry.imports:
            nm = imp.name.decode("latin1", "ignore") if imp.name else f"ord{imp.ordinal}"
            mp[imp.address] = f"{dll}!{nm}"
    return mp


def get_text(pe):
    for s in pe.sections:
        if s.Name.rstrip(b"\0") == b".text":
            return s.get_data(), pe.OPTIONAL_HEADER.ImageBase + s.VirtualAddress, s.Misc_VirtualSize
    raise RuntimeError("no .text")


def all_insns(code, va):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    return list(md.disasm(code, va))


def resolve_abs(ins):
    # operand absolute address 0x... for mov/push/lea
    m = re.search(r"0x([0-9a-fA-F]{8})", ins.op_str)
    if m:
        return int(m.group(1), 16)
    return None


def find_strings(data):
    pats = {
        "IIPSHostApp.exe": b"IIPSHostApp.exe",
        "IIPSERR_CACHE_INIT": b"IIPSERR_CACHE_INIT",
        "IIPSERR_ERROR_INIT": b"IIPSERR_ERROR_INIT",
        "LaunchIIPSHostApp failed": b"LaunchIIPSHostApp failed",
        "Failed to get function CreateIFSLibDll": b"Failed to get function CreateIFSLibDll",
        "Failed to create ifs lib": b"Failed to create ifs lib",
        "Failed to get proc DestoryIFSLibDll": b"Failed to get proc DestoryIFSLibDll",
        "CreateIFSLibDll": b"CreateIFSLibDll",
        "DestoryIFSLibDll": b"DestoryIFSLibDll",
        "ifs2.dll": b"ifs2.dll",
        "IIPS/IIPSHostApp.ini": b"IIPS/IIPSHostApp.ini",
        "IIPS/IIPSHostApp.exe": b"IIPS/IIPSHostApp.exe",
        "Global\\IIPSShareState_MMF_": b"Global\\IIPSShareState_MMF_",
        "Global\\IIPSShareState_Mutex_": b"Global\\IIPSShareState_Mutex_",
        "GetResourceManagerII": b"GetResourceManagerII",
        "ReleaseResourceManagerII": b"ReleaseResourceManagerII",
        "Environment List Box": b"Environment List Box",
        "iipsinit": b"iipsinit",
    }
    out = {}
    for label, pat in pats.items():
        idx = []
        start = 0
        while True:
            i = data.find(pat, start)
            if i < 0:
                break
            idx.append(i)
            start = i + 1
        out[label] = idx
    return out


def va_to_file(pe, va):
    for s in pe.sections:
        start = pe.OPTIONAL_HEADER.ImageBase + s.VirtualAddress
        end = start + max(s.Misc_VirtualSize, s.SizeOfRawData)
        if start <= va < end:
            return s.PointerToRawData + (va - start)
    return None


def file_to_va(pe, off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return pe.OPTIONAL_HEADER.ImageBase + s.VirtualAddress + (off - s.PointerToRawData)
    return None


def main():
    OUTLOG.mkdir(exist_ok=True)
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    data = IIPS.read_bytes()
    sha = hashlib.sha256(data).hexdigest().upper()
    pe = pefile.PE(str(IIPS))
    pe.parse_data_directories()
    base = pe.OPTIONAL_HEADER.ImageBase
    iat = iat_map(pe)
    iat_short = {k: v.replace(".dll", "") for k, v in iat.items()}
    code, text_va, text_size = get_text(pe)
    insns = all_insns(code, text_va)
    index = {i.address: i for i in insns}

    strmap = find_strings(data)
    str_va_to_label = {}
    for label, offs in strmap.items():
        for off in offs:
            va = file_to_va(pe, off)
            if va:
                str_va_to_label.setdefault(va, []).append(label)

    # collect relevant API calls
    api_hit = {}
    for ins in insns:
        if ins.mnemonic != "call":
            continue
        target = None
        if ins.op_str.startswith("dword ptr ["):
            m = re.search(r"0x([0-9a-fA-F]{8})", ins.op_str)
            if m:
                target = int(m.group(1), 16)
        if target is None:
            continue
        api = iat_short.get(target)
        if not api:
            continue
        api_hit.setdefault(api, []).append(ins.address)

    focus = [
        "KERNEL32!LoadLibraryW",
        "KERNEL32!FreeLibrary",
        "KERNEL32!GetProcAddress",
        "KERNEL32!GetModuleHandleA",
        "KERNEL32!GetModuleFileNameW",
        "KERNEL32!CreateFileA",
        "KERNEL32!CreateFileW",
        "KERNEL32!GetFileAttributesW",
        "KERNEL32!FindFirstFileW",
        "KERNEL32!FindNextFileW",
        "KERNEL32!DeleteFileW",
        "KERNEL32!CreateDirectoryW",
        "KERNEL32!GetPrivateProfileStringW",
        "KERNEL32!WritePrivateProfileStringW",
        "KERNEL32!CreateFileMappingA",
        "KERNEL32!OpenFileMappingA",
        "KERNEL32!OpenFileMappingW",
        "KERNEL32!MapViewOfFile",
        "KERNEL32!UnmapViewOfFile",
        "KERNEL32!CreateMutexA",
        "KERNEL32!OpenMutexW",
        "KERNEL32!CreateEventA",
        "KERNEL32!CreateEventW",
        "KERNEL32!SetEvent",
        "KERNEL32!WaitForSingleObject",
        "KERNEL32!WaitForMultipleObjects",
        "KERNEL32!CreateThread",
        "KERNEL32!GetEnvironmentVariable",
        "KERNEL32!ExpandEnvironmentStrings",
        "KERNEL32!SetCurrentDirectory",
        "USER32!CreateWindowExA",
        "USER32!MessageBoxW",
        "SHELL32!ShellExecuteExW",
        "ADVAPI32!OpenProcessToken",
        "ADVAPI32!LookupPrivilegeValueA",
        "ADVAPI32!AdjustTokenPrivileges",
    ]
    print("API_HIT_TOTAL", len(api_hit))
    for k in list(api_hit)[:10]:
        print("API_HIT_EXAMPLE", k, api_hit[k][:3])

    rows = []
    for api, addrs in sorted(api_hit.items()):
        if not (api in focus or api.startswith(("KERNEL32!CreateFile", "KERNEL32!GetFileAttributes", "KERNEL32!OpenFileMapping", "KERNEL32!CreateFileMapping", "KERNEL32!CreateMutex", "KERNEL32!OpenMutex", "KERNEL32!CreateEvent", "KERNEL32!WaitForSingleObject", "KERNEL32!WaitForMultipleObjects", "KERNEL32!CreateThread", "KERNEL32!GetModuleFileName", "KERNEL32!LoadLibrary", "KERNEL32!FreeLibrary", "KERNEL32!GetProcAddress"))):
            continue
        for va in addrs:
            pos = index[va]
            tail = []
            nexts = insns[insns.index(pos)+1:insns.index(pos)+14]
            for t in nexts:
                mark = ""
                if t.mnemonic in ("test", "cmp"):
                    mark = "BRANCH_CHK"
                elif t.mnemonic.startswith("j"):
                    mark = "BRANCH"
                tail.append({"va": hex(t.address), "op": f"{t.mnemonic} {t.op_str}", "mark": mark})
            # string loaded in previous up to 8 instructions
            prev = []
            previns = insns[max(0,insns.index(pos)-10):insns.index(pos)]
            for p in previns:
                absv = resolve_abs(p)
                labels = str_va_to_label.get(absv, []) if absv else []
                if labels:
                    prev.append({"va": hex(p.address), "op": f"{p.mnemonic} {p.op_str}", "string": ",".join(labels)})
            rows.append({
                "api": api,
                "callsite_va": hex(va),
                "prev": prev,
                "tail": tail,
            })

    print(f"IIPS_SHA256={sha}")
    print("RELEVANT_CALLS", len(rows))
    for r in rows:
        print(f"{r['api']} {r['callsite_va']}")
        for p in r["prev"]:
            print("  prev", p["va"], p["op"], "STRING", p.get("string", ""))
        for t in r["tail"]:
            print("  tail", t["va"], t["op"], t["mark"])

    # Save artifacts
    summary = OUTLOG / f"ex051_static_summary_{now}.log"
    contract = OUTLOG / "ex051_environment_contract.csv"
    statusflow = OUTLOG / "ex051_status_flow.csv"
    contract_ts = OUTLOG / f"ex051_environment_contract_{now}.csv"
    statusflow_ts = OUTLOG / f"ex051_status_flow_{now}.csv"
    callsjson = OUTLOG / f"ex051_api_callsites_{now}.json"

    summary_text = (
        "EX-051 static iips.dll scan\n"
        f"timestamp={now}\n"
        f"iips=SHA256={sha}\n"
        f"imagebase=0x{base:x}\n"
        f"entry=0x{pe.OPTIONAL_HEADER.AddressOfEntryPoint:x}\n"
        f"exports={[(hex(e.address), e.name.decode('latin1','ignore')) for e in getattr(pe,'DIRECTORY_ENTRY_EXPORT',[]).symbols]}\n"
        f"relevant_calls={len(rows)}\n"
    )
    summary.write_text(summary_text, encoding="utf-8")
    for r in rows:
        block = (
            f"{r['api']} {r['callsite_va']}\n"
            + "".join(f"  prev {p['va']} {p['op']} STRING={p.get('string','')}\n" for p in r["prev"])
            + "".join(f"  tail {t['va']} {t['op']} {t['mark']}\n" for t in r["tail"])
        )
        with open(summary, "a", encoding="utf-8", newline="\n") as f:
            f.write(block)

    contract_header = [
        "function_name", "function_rva", "function_va", "api_or_resource",
        "api_type", "callsite_rva", "return_value_used", "success_condition",
        "failure_condition", "failure_string", "next_state", "evidence_level",
        "confidence", "notes",
    ]
    status_header = [
        "state_id", "function_rva", "predecessor", "operation", "success_branch",
        "failure_branch", "status_value", "error_string", "next_state",
        "evidence_level", "notes",
    ]

    # Initial manual rows from confirmed EX-050 plus current static hits.
    known = [
        ["IIPS privilege setup helper", "0x51f0", "0x100051f0", "OpenProcessToken", "win32", "0x5208", "yes", "test eax,eax; je failure", "zero return", "", "PRIVILEGE_STATE", "L2", "MEDIUM", "branch shape at 0x1000520e"],
        ["IIPS privilege setup helper", "0x51f0", "0x100051f0", "LookupPrivilegeValueA", "win32", "0x5227", "yes", "test eax,eax; je failure", "zero return", "", "PRIVILEGE_STATE", "L2", "MEDIUM", "branch shape at 0x1000522d"],
        ["IIPS privilege setup helper", "0x51f0", "0x100051f0", "AdjustTokenPrivileges", "win32", "0x5260", "yes", "test eax,eax; je/getLastError path", "zero return or ERROR_NOT_ALL_ASSIGNED", "", "PRIVILEGE_STATE", "L2", "MEDIUM", "branch shape at 0x10005266"],
        ["CNIFS::InitInGameApp", "0x9860", "0x10009860", "QoS initialization helper 0x10006d20", "internal", "0x98cd", "yes", "test al,al; jne continue", "false result is logged but not fatal", "[CNIFS::InitInGameApp()][Failed to init qos (true)]", "QOS_INIT_STATE", "L2", "MEDIUM", "failure string 0x10034a34; control continues"],
        ["CNIFS::InitInGameApp", "0x9860", "0x10009860", "CNIFS::initIfsLib 0x10009570", "internal", "0x99d2", "yes", "test al,al; jne continue", "false result returns from InitInGameApp", "", "IFS2_LOAD_STATE", "L2", "HIGH", "failure propagation at 0x100099d7/0x100099d9"],
        ["CNIFS::InitInGameApp", "0x9860", "0x10009860", "IIPSHostApp.ini [ResPool] ReservedSize", "config", "0x9a8b", "yes", "GetPrivateProfileIntW result; default 0x40000000", "unresolved", "", "RESPOOL_CONFIG_STATE", "L2", "MEDIUM", "string refs 0x10034a68, 0x10034aa4, 0x10034a88; config file currently ReservedSize=0"],
        ["CNIFS::initIfsLib wrapper", "0x9570", "0x10009570", "KERNEL32.LoadLibraryW", "module", "0x96e9", "yes", "handle != NULL; jne 0x10009770", "NULL/FAILED", "[CNIFS::initIfsLib()][Failed to open dllfile][error %d][path %s]", "IFS2_LOAD_STATE", "L2", "CONFIRMED", "string xref 0x1000970d; ifs2.dll UTF-16 string near path builder"],
        ["CNIFS::initIfsLib wrapper", "0x9570", "0x10009570", "KERNEL32.GetProcAddress(\"CreateIFSLibDll\")", "module", "0x9777", "yes", "func != NULL", "NULL", "[CNIFS::initIfsLib()][Failed to get function CreateIFSLibDll]", "IFS2_RESOLVE", "L2", "CONFIRMED", "EX-050"],
        ["CNIFS::initIfsLib wrapper", "0x9570", "0x10009570", "CreateIFSLibDll", "api", "0x97a5", "yes", "nonzero EAX", "zero EAX", "[CNIFS::initIfsLib()][Failed to create ifs lib]", "IFS2_CREATE", "L2", "CONFIRMED", "EX-050"],
        ["CNIFS::initIfsLib wrapper", "0x9570", "0x10009570", "KERNEL32.GetProcAddress(\"DestoryIFSLibDll\")", "module", "0x97cc", "yes", "func != NULL", "NULL", "[CNIFS::initIfsLib()][Failed to get proc DestoryIFSLibDll]", "IFS2_DESTROY_PROBE", "L2", "CONFIRMED", "EX-050"],
        ["ResourceManagerII::LaunchIIPSHostApp candidate", "0x15a00", "0x10015a00", "SHELL32.ShellExecuteExW", "process", "0x15cd1", "yes", "test eax,eax; je failure; result > 0x20", "zero return or ShellExecute result <= 0x20", "[ResourceManagerII::LaunchIIPSHostApp()][LaunchIIPSHostApp failed][error %d][sExec.hInstApp %d]", "HOSTAPP_LAUNCH_STATE", "L2", "MEDIUM", "success string at 0x10037308; failure string at 0x10037350"],
        ["IIPS share-state object manager", "0x11930", "0x10011930", "Global\\IIPSShareState_MMF_ object name", "named-object", "0x11b18", "yes", "OpenFileMappingA/Mapping handle path", "handle branch unresolved", "", "SHARE_STATE_MMF", "L2", "MEDIUM", "string ref followed by OpenFileMappingA at 0x1001194e"],
        ["IIPS share-state object manager", "0x11930", "0x10011930", "Global\\IIPSShareState_Mutex_ object name", "named-object", "0x11c98", "yes", "CreateMutexA handle != NULL", "NULL handle", "", "SHARE_STATE_MUTEX", "L2", "MEDIUM", "string ref followed by CreateMutexA at 0x1001197b"],
        ["IIPS error/cache initialization", "unknown", "unknown", "IIPSERR_CACHE_INIT", "log/status", "unknown", "no direct text xref", "unresolved", "unresolved", "IIPSERR_CACHE_INIT]", "CACHE_INIT_UNRESOLVED", "L0/L1", "LOW", "string exists at 0x10035b8a; no direct .text xref recovered"],
        ["IIPS error/cache initialization", "unknown", "unknown", "IIPSERR_ERROR_INIT", "log/status", "unknown", "no direct text xref", "unresolved", "unresolved", "IIPSERR_ERROR_INIT]", "ERROR_INIT_UNRESOLVED", "L0/L1", "LOW", "38 string occurrences; no direct .text xref recovered"],
    ]
    for out in (contract, contract_ts):
        with open(out, "w", encoding="utf-8", newline="") as f:
            wr = csv.writer(f, lineterminator="\n")
            wr.writerow(contract_header)
            wr.writerows(known)

    status_rows = [
        ["IIPS_INIT_ENTRY", "0x9570", "EXE/TVM boundary", "entry into CNIFS init wrapper", "IFS2_LOAD_STATE", "ERROR_STATE", "unknown", "", "IFS2_LOAD_STATE", "L2", "static candidate"],
        ["QOS_INIT_STATE", "0x98cd", "IIPS_INIT_ENTRY", "init QoS helper", "CONTINUE", "LOG_ONLY", "helper result", "Failed to init qos (true)", "IFS2_LOAD_STATE", "L2", "non-fatal at this call site"],
        ["RESPOOL_CONFIG_STATE", "0x9a8b", "IFS2_RESOLVE", "read IIPSHostApp.ini [ResPool] ReservedSize", "CONTINUE", "CONTINUE", "integer/default 0x40000000", "", "RESOURCE_POOL_INIT", "L2", "runtime value not captured"],
        ["IFS2_LOAD_STATE", "0x96e9", "IIPS_INIT_ENTRY", "LoadLibraryW(ifs2 path)", "IFS2_RESOLVE", "IIPS_ERR_OPEN_DLL", "handle != NULL", "Failed to open dllfile", "IFS2_RESOLVE or ERROR_STATE", "L2", "confirmed branch at 0x100096ef/0x100096f4; string ref at 0x1000970d"],
        ["IFS2_RESOLVE", "0x9777", "IFS2_LOAD_STATE", "GetProcAddress(CreateIFSLibDll)", "IFS2_CREATE", "IIPS_ERR_RESOLVE_CREATE", "func != NULL", "Failed to get function CreateIFSLibDll", "IFS2_CREATE or ERROR_STATE", "L2", "confirmed branch at 0x1000977e/0x10009783"],
        ["IFS2_CREATE", "0x97a5", "IFS2_RESOLVE", "call CreateIFSLibDll", "IFS2_DESTROY", "IIPS_ERR_CREATE_IFS", "nonzero EAX", "Failed to create ifs lib", "IFS2_DESTROY_PROBE or ERROR_STATE", "L2", "confirmed branch at 0x100097a7/0x100097ac"],
        ["IFS2_DESTROY_PROBE", "0x97cc", "IFS2_CREATE", "GetProcAddress(DestoryIFSLibDll)", "CNIFS_RELEASE", "IIPS_ERR_DESTROY_RESOLVE", "func != NULL", "Failed to get proc DestoryIFSLibDll", "CNIFS_RELEASE or ERROR_STATE", "L2", "confirmed branch at 0x100097d3"],
        ["HOSTAPP_LAUNCH_STATE", "0x15cd1", "RESOURCE_MANAGER_INIT", "ShellExecuteExW(host app)", "HOSTAPP_RUNNING", "HOSTAPP_LAUNCH_FAILED", "ShellExecuteExW true and hInstApp > 0x20", "LaunchIIPSHostApp failed", "HOSTAPP_RUNNING or ERROR_STATE", "L2", "static branch only; runtime not observed"],
        ["CACHE_INIT_STATE", "unknown", "IIPS_INIT_ENTRY", "IIPSERR_CACHE_INIT handling", "unresolved", "unresolved", "unknown", "IIPSERR_CACHE_INIT]", "UNRESOLVED", "L0/L1", "no direct xref recovered"],
        ["ERROR_INIT_STATE", "unknown", "IIPS_INIT_ENTRY", "IIPSERR_ERROR_INIT handling", "unresolved", "unresolved", "unknown", "IIPSERR_ERROR_INIT]", "UNRESOLVED", "L0/L1", "no direct xref recovered"],
    ]
    for out in (statusflow, statusflow_ts):
        with open(out, "w", encoding="utf-8", newline="") as f:
            wr = csv.writer(f, lineterminator="\n")
            wr.writerow(status_header)
            wr.writerows(status_rows)

    callsjson.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WROTE", summary, contract, statusflow, callsjson)


if __name__ == "__main__":
    main()
