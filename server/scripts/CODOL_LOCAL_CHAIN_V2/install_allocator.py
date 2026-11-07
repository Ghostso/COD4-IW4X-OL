# -*- coding: utf-8 -*-
"""安装 CRT 分配器钩子，让 GetLSG() 能正常工作。

根因：
  [0xE85C0C] = 0  →  operator new (0xB74220) 直接返回 NULL
                  →  GetLSG (0x803830) 失败
                  →  [0x08269774] 永远 0

修复：
  客户端自带安装函数 0xB76D80(flag)，
  它会装入 0xB78820(new) / 0xB741C0(delete) / 0xB788A0(free) 等。

  方法 A（推荐）：直接写三个全局，不用远程调用
     [0xE85C0C] = 0xB78820   (new)
     [0xE85C10] = 0xB788D0   (free，见 0xB74240 的实现)
     [0xE85C18] = 0xB788A0   (delete，见 0xB741C0 写的是 0xE85C18)
     并置 [0xE85C28] = 1     (已安装标志)

用法:
  python install_allocator.py --pid <pid>
  python install_allocator.py --pid <pid> --restore
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import struct
import subprocess
import sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
PROC = 0x0008 | 0x0010 | 0x0020 | 0x0400
PAGE = 0x40

k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualProtectEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                                 wt.DWORD, ctypes.POINTER(wt.DWORD)]

# 全局 -> 目标函数
PLAN = [
    (0xE85C0C, 0xB78820, "new"),
    (0xE85C10, 0xB788D0, "free"),
    (0xE85C18, 0xB788A0, "delete"),
]
FLAG_G = 0xE85C28


def find_pid():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_client_shipRetail.exe",
                          "/FO", "CSV", "/NH"], capture_output=True, text=True,
                         errors="replace").stdout
    return [int(x.strip('"').split('","')[1]) for x in out.splitlines()
            if '","' in x and x.split('","')[0].strip('"').lower() == "codomp_client_shipretail.exe"]


def rd(h, a, n):
    b = ctypes.create_string_buffer(n)
    g = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g)):
        return None
    return b.raw[:g.value]


def wr(h, a, data):
    old = wt.DWORD()
    if not k32.VirtualProtectEx(h, ctypes.c_void_p(a), len(data), PAGE, ctypes.byref(old)):
        return False
    g = ctypes.c_size_t()
    ok = k32.WriteProcessMemory(h, ctypes.c_void_p(a), data, len(data), ctypes.byref(g))
    k32.VirtualProtectEx(h, ctypes.c_void_p(a), len(data), old.value, ctypes.byref(wt.DWORD()))
    return bool(ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--restore", action="store_true")
    a = ap.parse_args()

    pid = a.pid
    if not pid:
        ps = find_pid()
        if not ps:
            print("no client")
            return 2
        pid = max(ps)

    h = k32.OpenProcess(PROC, False, pid)
    if not h:
        print("OpenProcess failed err=%d" % ctypes.get_last_error())
        return 2

    print("pid=%d" % pid)
    print("--- 安装前 ---")
    for g, fn, name in PLAN:
        raw = rd(h, g, 4)
        print("  [0x%08X] %-7s = %s" % (g, name, raw.hex() if raw else "?"))
    raw = rd(h, FLAG_G, 1)
    print("  [0x%08X] flag    = %s" % (FLAG_G, raw.hex() if raw else "?"))

    print()
    if a.restore:
        for g, fn, name in PLAN:
            wr(h, g, struct.pack("<I", 0))
            print("  restore [0x%08X] = 0" % g)
        wr(h, FLAG_G, b"\x00")
        print("  restore flag = 0")
        return 0

    ok_all = True
    for g, fn, name in PLAN:
        if not wr(h, g, struct.pack("<I", fn)):
            print("  !! 写 [0x%08X] 失败" % g)
            ok_all = False
        else:
            print("  [0x%08X] %-7s <- 0x%08X" % (g, name, fn))
    if not wr(h, FLAG_G, b"\x01"):
        print("  !! 写 flag 失败")
        ok_all = False
    else:
        print("  [0x%08X] flag    <- 1" % FLAG_G)

    print()
    print("--- 安装后回读 ---")
    for g, fn, name in PLAN:
        raw = rd(h, g, 4)
        v = struct.unpack("<I", raw)[0] if raw else 0
        mark = "OK" if v == fn else "MISMATCH"
        print("  [0x%08X] %-7s = 0x%08X  %s" % (g, name, v, mark))
    raw = rd(h, FLAG_G, 1)
    print("  [0x%08X] flag    = %s" % (FLAG_G, raw.hex() if raw else "?"))

    k32.CloseHandle(h)
    return 0 if ok_all else 5


if __name__ == "__main__":
    sys.exit(main())
