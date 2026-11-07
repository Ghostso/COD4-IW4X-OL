#!/usr/bin/env python3
"""138 诊断: 对当前活着的客户端试读几个关键地址（只读，不注入，不启动）。
分别试: 单次 4B / 单次 64KB / 分块 4KB —— 打印值与 GetLastError。
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PE32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
                ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", wt.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
TARGET = "codoMP_client_shipRetail.exe"


def pids():
    h = k32.CreateToolhelp32Snapshot(2, 0)
    out = []
    e = PE32()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32FirstW(h, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == TARGET.lower():
            out.append(int(e.th32ProcessID))
        ok = k32.Process32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return out


ps = pids()
print("客户端 pids =", ps)
if not ps:
    print("客户端未运行 -> 需新一轮启动后才能试")
    raise SystemExit(0)
pid = ps[0]
for access, label in ((0x400 | 0x10, "QUERY|VM_READ"),
                      (0x1F0FFF, "ALL_ACCESS")):
    h = k32.OpenProcess(access, False, pid)
    err = ctypes.get_last_error()
    print("OpenProcess(%s) -> h=%s err=%d" % (label, h, err))
    if not h:
        continue
    for va, name in ((0x0849BA30, "roomGate"), (0x08269774, "connSlot"),
                     (0x00E59D20, "appMode"), (0x00400000, "exeBase")):
        got = ctypes.c_size_t(0)
        b4 = ctypes.create_string_buffer(4)
        ctypes.set_last_error(0)
        ok = k32.ReadProcessMemory(h, ctypes.c_void_p(va), b4, 4, ctypes.byref(got))
        print("  RPM 4B @%08X %-8s ok=%s got=%d err=%d val=%s"
              % (va, name, bool(ok), got.value, ctypes.get_last_error(),
                 b4.raw.hex() if ok else "-"))
    # 大块 vs 分块
    big = ctypes.create_string_buffer(0x10000)
    got = ctypes.c_size_t(0)
    ctypes.set_last_error(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(0x00400000), big, 0x10000,
                               ctypes.byref(got))
    print("  RPM 64KB @0x400000 ok=%s got=%d err=%d"
          % (bool(ok), got.value, ctypes.get_last_error()))
    n_ok = 0
    for off in range(0, 0x10000, 0x1000):
        g2 = ctypes.c_size_t(0)
        if k32.ReadProcessMemory(h, ctypes.c_void_p(0x00400000 + off),
                                 ctypes.create_string_buffer(0x1000), 0x1000,
                                 ctypes.byref(g2)) and g2.value == 0x1000:
            n_ok += 1
    print("  分块 4KB x16 成功 = %d/16" % n_ok)
    k32.CloseHandle(h)
