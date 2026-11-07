"""Read-only live-memory scan for the TenProtect VSD loader strings.

Starts a sandbox client, lets it reach the TP VSD check, scans readable
committed regions for the exact ASCII/UTF-16 loader strings, records their
runtime addresses and module ownership, then terminates the test process.

Usage:
  python -X utf8 CODOLServer/_mainline/scan_live_vsd_loader.py \
    --exe <sandbox exe> --cwd <sandbox> --out <json>
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import struct
import time
from pathlib import Path


CREATE_SUSPENDED = 0x00000004
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_TERMINATE = 0x0001
LIST_MODULES_ALL = 0x03
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


k32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD),
        ("dwXCountChars", wt.DWORD), ("dwYCountChars", wt.DWORD),
        ("dwFillAttribute", wt.DWORD), ("dwFlags", wt.DWORD),
        ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD),
        ("lpReserved2", ctypes.c_void_p), ("hStdInput", wt.HANDLE),
        ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wt.HANDLE), ("hThread", wt.HANDLE),
        ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD),
    ]


class MODULEINFO(ctypes.Structure):
    _fields_ = [
        ("lpBaseOfDll", ctypes.c_void_p),
        ("SizeOfImage", wt.DWORD),
        ("EntryPoint", ctypes.c_void_p),
    ]


class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("_pad0", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
        ("_pad1", wt.DWORD),
    ]


k32.CreateProcessW.restype = wt.BOOL
k32.CreateProcessW.argtypes = [
    wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL,
    wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p,
]
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [
    wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [
    wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t,
]
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]

psapi.EnumProcessModulesEx.restype = wt.BOOL
psapi.EnumProcessModulesEx.argtypes = [
    wt.HANDLE, ctypes.POINTER(wt.HMODULE), wt.DWORD,
    ctypes.POINTER(wt.DWORD), wt.DWORD,
]
psapi.GetModuleInformation.restype = wt.BOOL
psapi.GetModuleInformation.argtypes = [
    wt.HANDLE, wt.HMODULE, ctypes.POINTER(MODULEINFO), wt.DWORD,
]
psapi.GetModuleBaseNameW.restype = wt.DWORD
psapi.GetModuleBaseNameW.argtypes = [
    wt.HANDLE, wt.HMODULE, wt.LPWSTR, wt.DWORD,
]


def modules(hproc):
    needed = wt.DWORD()
    arr = (wt.HMODULE * 2048)()
    if not psapi.EnumProcessModulesEx(
            hproc, arr, ctypes.sizeof(arr), ctypes.byref(needed),
            LIST_MODULES_ALL):
        return []
    out = []
    for i in range(needed.value // ctypes.sizeof(wt.HMODULE)):
        name = ctypes.create_unicode_buffer(260)
        psapi.GetModuleBaseNameW(hproc, arr[i], name, len(name))
        info = MODULEINFO()
        if not psapi.GetModuleInformation(
                hproc, arr[i], ctypes.byref(info), ctypes.sizeof(info)):
            continue
        out.append({
            "name": name.value,
            "base": int(info.lpBaseOfDll or 0),
            "size": int(info.SizeOfImage),
        })
    return out


def owner(mods, va):
    for m in mods:
        if m["base"] <= va < m["base"] + m["size"]:
            return "%s+0x%X" % (m["name"], va - m["base"])
    return "private/unknown"


def find_all(blob, needle):
    out = []
    pos = 0
    while True:
        i = blob.find(needle, pos)
        if i < 0:
            return out
        out.append(i)
        pos = i + 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--wait", type=float, default=3.0)
    args = ap.parse_args()

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmd = ctypes.create_unicode_buffer('"%s" -q' % args.exe)
    if not k32.CreateProcessW(
            args.exe, cmd, None, None, True, CREATE_SUSPENDED, None,
            args.cwd, ctypes.byref(si), ctypes.byref(pi)):
        raise SystemExit("CreateProcessW failed: %d" % ctypes.get_last_error())
    h = k32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_TERMINATE,
        False, pi.dwProcessId)
    if not h:
        k32.TerminateProcess(pi.hProcess, 1)
        raise SystemExit("OpenProcess failed: %d" % ctypes.get_last_error())
    k32.ResumeThread(pi.hThread)
    time.sleep(args.wait)

    mods = modules(h)
    needles = {
        "vsd_ascii": b"VSDDrvDLLD.dll",
        "vsd_wide": "VSDDrvDLLD.dll".encode("utf-16le"),
        "create_ascii": b"DLLCreateVSDIDrvObj",
        "create_wide": "DLLCreateVSDIDrvObj".encode("utf-16le"),
    }
    hits = {k: [] for k in needles}
    regions = []
    addr = 0x10000
    maxaddr = 0x7FFF0000
    while addr < maxaddr:
        mbi = MBI()
        got = k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                 ctypes.sizeof(mbi))
        if not got:
            break
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if size <= 0:
            break
        if (mbi.State == MEM_COMMIT and not (mbi.Protect & PAGE_GUARD)
                and (mbi.Protect & 0xFF) != PAGE_NOACCESS and size <= 0x4000000):
            data = bytearray()
            pos = 0
            while pos < size:
                n = min(0x100000, size - pos)
                buf = ctypes.create_string_buffer(n)
                read = ctypes.c_size_t()
                ok = k32.ReadProcessMemory(
                    h, ctypes.c_void_p(base + pos), buf, n,
                    ctypes.byref(read))
                if ok and read.value == n:
                    data.extend(buf.raw)
                else:
                    data.extend(b"\x00" * n)
                pos += n
            blob = bytes(data)
            regions.append({"base": base, "size": size,
                            "protect": int(mbi.Protect),
                            "type": int(mbi.Type)})
            for label, needle in needles.items():
                for off in find_all(blob, needle)[:64]:
                    va = base + off
                    hits[label].append({
                        "va": va,
                        "owner": owner(mods, va),
                        "region": hex(base),
                        "protect": int(mbi.Protect),
                    })
        nxt = base + size
        if nxt <= addr:
            break
        addr = nxt

    # Locate code references to the private-mapped strings.  A direct
    # push/lea of the runtime VA appears as the same dword in executable
    # memory; this is the most direct way to find the TP loader function.
    xrefs = {}
    for label, records in hits.items():
        xrefs[label] = []
        for rec in records:
            target = rec["va"]
            pat = struct.pack("<I", target)
            addr2 = 0x10000
            while addr2 < maxaddr:
                mbi2 = MBI()
                got2 = k32.VirtualQueryEx(
                    h, ctypes.c_void_p(addr2), ctypes.byref(mbi2),
                    ctypes.sizeof(mbi2))
                if not got2:
                    break
                base2 = int(mbi2.BaseAddress or 0)
                size2 = int(mbi2.RegionSize)
                if size2 <= 0:
                    break
                protect = int(mbi2.Protect)
                executable = (protect & 0x10) or (protect & 0x20) or (protect & 0x40)
                if (mbi2.State == MEM_COMMIT and executable
                        and not (protect & PAGE_GUARD)
                        and size2 <= 0x4000000):
                    pos2 = 0
                    while pos2 < size2:
                        n2 = min(0x100000, size2 - pos2)
                        buf2 = ctypes.create_string_buffer(n2)
                        read2 = ctypes.c_size_t()
                        ok2 = k32.ReadProcessMemory(
                            h, ctypes.c_void_p(base2 + pos2), buf2, n2,
                            ctypes.byref(read2))
                        if ok2 and read2.value == n2:
                            blob2 = buf2.raw
                            off2 = 0
                            while True:
                                j = blob2.find(pat, off2)
                                if j < 0:
                                    break
                                ref_va = base2 + pos2 + j
                                xrefs[label].append({
                                    "target": target,
                                    "ref": ref_va,
                                    "owner": owner(mods, ref_va),
                                })
                                off2 = j + 1
                        pos2 += n2
                nxt2 = base2 + size2
                if nxt2 <= addr2:
                    break
                addr2 = nxt2

    report = {
        "pid": int(pi.dwProcessId),
        "module_count": len(mods),
        "regions_scanned": len(regions),
        "needles": hits,
        "xrefs": xrefs,
    }
    k32.TerminateProcess(h, 1)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
