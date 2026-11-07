# -*- coding: utf-8 -*-
"""Read-only second-round runtime dump and static comparison."""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import capstone
import pefile

TARGET = "codoMP_client_shipRetail.exe"
STILL_ACTIVE = 259
PAGE_GUARD = 0x100
MEM_COMMIT = 0x1000
PAGE_EXECUTE = 0x10
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD),
                ("th32ProcessID", wt.DWORD), ("GlblcntUsage", wt.DWORD),
                ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE),
                ("szModule", ctypes.c_wchar * 256),
                ("szExePath", ctypes.c_wchar * 260)]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.GetExitCodeProcess.restype = wt.BOOL
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Module32FirstW.restype = wt.BOOL
k32.Module32NextW.restype = wt.BOOL
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.CloseHandle.restype = wt.BOOL


def read_mem(proc, address, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    if k32.ReadProcessMemory(proc, ctypes.c_void_p(address), buf, size, ctypes.byref(got)):
        return buf.raw[:got.value]
    return b""


def modules(pid):
    snap = k32.CreateToolhelp32Snapshot(0x08 | 0x10, pid)
    if not snap or snap in (-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
        return []
    me = MODULEENTRY32W(); me.dwSize = ctypes.sizeof(me); rows = []
    try:
        if k32.Module32FirstW(snap, ctypes.byref(me)):
            while True:
                rows.append({"name": me.szModule, "base": int(me.modBaseAddr or 0),
                             "size": int(me.modBaseSize), "path": me.szExePath})
                if not k32.Module32NextW(snap, ctypes.byref(me)):
                    break
    finally:
        k32.CloseHandle(snap)
    return rows


def pids():
    raw = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + TARGET,
                          "/FO", "CSV", "/NH"], capture_output=True,
                         text=True, errors="replace").stdout
    out = []
    for line in raw.splitlines():
        cols = [x.strip('"') for x in line.split('","')]
        if cols and cols[0].casefold() == TARGET.casefold():
            try: out.append(int(cols[1].replace(",", "")))
            except (IndexError, ValueError): pass
    return out


def pages(proc, base, size):
    rows = []; address = base; end = base + size
    while address < end:
        mbi = MEMORY_BASIC_INFORMATION()
        if not k32.VirtualQueryEx(proc, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        b = int(mbi.BaseAddress or address); n = int(mbi.RegionSize or 0)
        if n <= 0: break
        rows.append({"base": b, "size": n, "state": int(mbi.State),
                     "protect": int(mbi.Protect), "type": int(mbi.Type),
                     "executable": bool(mbi.Protect & 0xF0),
                     "private": int(mbi.Type) == 0x20000})
        address = b + n
    return rows


def sha(data):
    return hashlib.sha256(data).hexdigest() if data else ""


def disasm(data, address, count=12):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    out = []
    for ins in md.disasm(data, address):
        out.append({"address": hex(ins.address), "bytes": ins.bytes.hex(" "),
                    "mnemonic": ins.mnemonic, "op_str": ins.op_str})
        if len(out) >= count: break
    return out


def disk_text(path):
    try:
        pe = pefile.PE(str(path), fast_load=True)
        image_base = int(pe.OPTIONAL_HEADER.ImageBase)
        entry = int(pe.OPTIONAL_HEADER.AddressOfEntryPoint)
        sections = [{"name": s.Name.rstrip(b"\0").decode("ascii", "replace"),
                     "rva": int(s.VirtualAddress), "raw": int(s.PointerToRawData),
                     "raw_size": int(s.SizeOfRawData), "virtual_size": int(s.Misc_VirtualSize),
                     "characteristics": int(s.Characteristics)} for s in pe.sections]
        pe.close()
        return {"image_base": image_base, "entry_rva": entry,
                "sections": sections, "sha256": sha(path.read_bytes())}
    except Exception as exc:
        return {"error": repr(exc)}


def find_pid(wait):
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        current = pids()
        if len(current) == 1: return current[0]
        time.sleep(0.25)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--game-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--wait", type=float, default=90)
    args = ap.parse_args()
    game = Path(args.game_root).resolve(); out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    pid = args.pid or find_pid(args.wait)
    if not pid: raise SystemExit("client PID not found")
    proc = k32.OpenProcess(0x0410, False, pid)
    if not proc: raise SystemExit("OpenProcess failed: %d" % ctypes.get_last_error())
    try:
        mods = modules(pid)
        by_name = {m["name"].casefold(): m for m in mods}
        manifest = {"pid": pid, "captured_at": time.time(), "modules": mods, "targets": {}, "pages": {}}
        for key, needles in {"client": [TARGET], "base_dll": ["codoMP_client_shipRetailBase.dll"],
                             "iips": ["iips.dll"], "bootstrapper": ["Bootstrapper32.dll"],
                             "localnet": ["CodolGameServer.Localnet32"]}.items():
            mod = next((m for m in mods if any(n.casefold() in m["name"].casefold() for n in needles)), None)
            if not mod: continue
            data = read_mem(proc, mod["base"], mod["size"])
            image = out / (key + "_runtime.bin"); image.write_bytes(data)
            manifest["targets"][key] = {**mod, "runtime_file": str(image),
                                         "runtime_size": len(data), "runtime_sha256": sha(data),
                                         "disk": disk_text(Path(mod["path"])) if mod.get("path") else {}}
            manifest["pages"][key] = pages(proc, mod["base"], mod["size"])
            if data:
                manifest["targets"][key]["entry_disasm"] = disasm(data[:96], mod["base"], 16)
        page_rows = []
        for key, target in manifest["targets"].items():
            for row in manifest["pages"].get(key, []):
                if row["state"] == MEM_COMMIT and row["executable"]:
                    blob = read_mem(proc, row["base"], min(row["size"], 0x200000))
                    page_file = out / (key + "_page_%08X.bin" % row["base"])
                    page_file.write_bytes(blob)
                    page_rows.append({"target": key, **row, "file": str(page_file), "sha256": sha(blob)})
        manifest["executable_pages"] = page_rows
        (out / "dump_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        report = {"pid": pid, "captured_at": manifest["captured_at"], "exit_code": None,
                  "important_bases": {k: v.get("base") for k, v in manifest["targets"].items()},
                  "target_count": len(manifest["targets"]), "executable_page_count": len(page_rows),
                  "ports": subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                                           errors="replace").stdout.splitlines()}
        (out / "reverse_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"pid": pid, "out": str(out), "targets": list(manifest["targets"]),
                          "executable_pages": len(page_rows)}, ensure_ascii=False))
    finally:
        k32.CloseHandle(proc)


if __name__ == "__main__":
    main()
