# -*- coding: utf-8 -*-
"""定位 0x239B120 属于哪个模块。"""
import ctypes
import ctypes.wintypes as wt
import sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)
QUERY = 0x0400
VM_READ = 0x0010
ALL_MODULES = 0x03
MAX_PATH = 260
TARGETS = (0x239B120, 0x1E2D338, 0xE5C8C0, 0x49D3B0, 0x49D3D0)


class MODULEINFO(ctypes.Structure):
    _fields_ = [("lpBaseOfDll", ctypes.c_void_p),
                ("SizeOfImage", wt.DWORD),
                ("EntryPoint", ctypes.c_void_p)]


def find_pid(name):
    arr = (wt.DWORD * 8192)()
    need = wt.DWORD()
    if not psapi.EnumProcesses(ctypes.byref(arr), ctypes.sizeof(arr),
                               ctypes.byref(need)):
        return 0
    for i in range(need.value // ctypes.sizeof(wt.DWORD)):
        h = k32.OpenProcess(QUERY | VM_READ, False, arr[i])
        if not h:
            continue
        try:
            buf = ctypes.create_unicode_buffer(MAX_PATH)
            if psapi.GetModuleBaseNameW(h, None, buf, MAX_PATH):
                if buf.value.lower().startswith(name.lower()):
                    return arr[i]
        finally:
            k32.CloseHandle(h)
    return 0


def list_modules(pid):
    h = k32.OpenProcess(QUERY | VM_READ, False, pid)
    if not h:
        return []
    try:
        arr = (ctypes.c_void_p * 2048)()
        need = wt.DWORD()
        if not psapi.EnumProcessModulesEx(h, ctypes.byref(arr),
                                          ctypes.sizeof(arr),
                                          ctypes.byref(need), ALL_MODULES):
            return []
        out = []
        for i in range(need.value // ctypes.sizeof(ctypes.c_void_p)):
            mi = MODULEINFO()
            if not psapi.GetModuleInformation(h, arr[i], ctypes.byref(mi),
                                              ctypes.sizeof(mi)):
                continue
            buf = ctypes.create_unicode_buffer(MAX_PATH)
            psapi.GetModuleBaseNameW(h, arr[i], buf, MAX_PATH)
            out.append((int(mi.lpBaseOfDll), mi.SizeOfImage, buf.value))
        return out
    finally:
        k32.CloseHandle(h)


def main():
    pid = find_pid("codoMP_client_shipRetail")
    if not pid:
        print("进程未运行")
        return 1
    print("pid = %d" % pid)
    mods = list_modules(pid)
    print("模块数 %d" % len(mods))
    for base, size, nm in sorted(mods, key=lambda x: -x[1])[:12]:
        print("  0x%08X..0x%08X %-40s %d" % (base, base + size, nm, size))
    print()
    for t in TARGETS:
        hit = None
        for base, size, nm in mods:
            if base <= t < base + size:
                hit = (nm, base, size)
                break
        if hit:
            print("0x%08X -> %s 偏移 0x%X" % (t, hit[0], t - hit[1]))
        else:
            print("0x%08X -> 不在模块内" % t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
