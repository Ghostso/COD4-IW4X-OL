"""Dump Base.dll from a suspended/resumed sandbox client and find VSD refs.

Read-only against the target process:
  CreateProcessW(CREATE_SUSPENDED) -> OpenProcess(READ|QUERY) -> ResumeThread
  -> wait for codoMP_client_shipRetailBase.dll -> ReadProcessMemory
  -> terminate test process.

The output is a module dump plus a JSON report of ASCII VSDDrvDll and
CreateVSDIDrvObj strings and their image-relative xrefs.

Usage:
  python -X utf8 CODOLServer/_mainline/dump_vsd_callsite.py \
    --exe <sandbox exe> --cwd <sandbox> --out <dir> --seconds 12
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import struct
import time
from pathlib import Path


CREATE_SUSPENDED = 0x00000004
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_TERMINATE = 0x0001
LIST_MODULES_ALL = 0x03


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
    arr = (wt.HMODULE * 1024)()
    if not psapi.EnumProcessModulesEx(
            hproc, arr, ctypes.sizeof(arr), ctypes.byref(needed),
            LIST_MODULES_ALL):
        return []
    count = needed.value // ctypes.sizeof(wt.HMODULE)
    out = []
    for i in range(count):
        name = ctypes.create_unicode_buffer(260)
        psapi.GetModuleBaseNameW(hproc, arr[i], name, len(name))
        info = MODULEINFO()
        if not psapi.GetModuleInformation(
                hproc, arr[i], ctypes.byref(info), ctypes.sizeof(info)):
            continue
        out.append({
            "handle": int(arr[i] or 0),
            "name": name.value,
            "base": int(info.lpBaseOfDll or 0),
            "size": int(info.SizeOfImage),
        })
    return out


def read_span(hproc, base: int, size: int) -> bytes:
    out = bytearray()
    pos = 0
    while pos < size:
        chunk = min(0x100000, size - pos)
        buf = ctypes.create_string_buffer(chunk)
        got = ctypes.c_size_t()
        ok = k32.ReadProcessMemory(
            hproc, ctypes.c_void_p(base + pos), buf, chunk,
            ctypes.byref(got))
        if ok and got.value == chunk:
            out.extend(buf.raw)
        else:
            out.extend(b"\x00" * chunk)
        pos += chunk
    return bytes(out)


def find_all(blob: bytes, needle: bytes):
    out = []
    pos = 0
    while True:
        i = blob.find(needle, pos)
        if i < 0:
            return out
        out.append(i)
        pos = i + 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seconds", type=float, default=12.0)
    parser.add_argument("--settle", type=float, default=2.0,
                        help="seconds to wait after Base.dll is mapped")
    args = parser.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmdline = ctypes.create_unicode_buffer('"%s" -q' % args.exe)
    if not k32.CreateProcessW(
            args.exe, cmdline, None, None, True, CREATE_SUSPENDED, None,
            args.cwd, ctypes.byref(si), ctypes.byref(pi)):
        raise SystemExit("CreateProcessW failed: %d" % ctypes.get_last_error())

    hproc = k32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_TERMINATE,
        False, pi.dwProcessId)
    if not hproc:
        k32.TerminateProcess(pi.hProcess, 1)
        raise SystemExit("OpenProcess failed: %d" % ctypes.get_last_error())

    k32.ResumeThread(pi.hThread)
    deadline = time.time() + args.seconds
    found = None
    while time.time() < deadline:
        for mod in modules(hproc):
            if mod["name"].lower() == "codomp_client_shipretailbase.dll":
                found = mod
                break
        if found and found["size"] > 0x1000000:
            break
        time.sleep(0.1)
    if not found:
        k32.TerminateProcess(hproc, 1)
        raise SystemExit("Base.dll was not observed")

    time.sleep(args.settle)
    blob = read_span(hproc, found["base"], found["size"])
    k32.TerminateProcess(hproc, 1)

    dump_path = outdir / "codoMP_client_shipRetailBase.image.bin"
    dump_path.write_bytes(blob)

    needles = {
        "vsd_dll_ascii": b"VSDDrvDll.dll",
        "vsd_dll_wide": "VSDDrvDll.dll".encode("utf-16le"),
        "create_ascii": b"CreateVSDIDrvObj",
        "create_wide": "CreateVSDIDrvObj".encode("utf-16le"),
        "release_ascii": b"ReleaseVSDIDrvObj",
        "release_wide": "ReleaseVSDIDrvObj".encode("utf-16le"),
    }
    report = {
        "pid": int(pi.dwProcessId),
        "module": found,
        "dump": str(dump_path),
        "needles": {},
    }
    for label, needle in needles.items():
        hits = find_all(blob, needle)
        records = []
        for off in hits[:64]:
            va = found["base"] + off
            pat = struct.pack("<I", va)
            refs = [found["base"] + x for x in find_all(blob, pat)]
            records.append({
                "off": off,
                "va": va,
                "dword_refs": refs[:64],
            })
        report["needles"][label] = {
            "count": len(hits),
            "hits": records,
        }

    report_path = outdir / "vsd_callsite.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("dump:", dump_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
