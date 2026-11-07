# -*- coding: utf-8 -*-
"""在运行中的客户端里读关键全局，验证静态分析。

用法: python probe_globals.py --pid <pid>
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import struct
import subprocess
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
PROC = 0x0008 | 0x0010 | 0x0020 | 0x0400
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

GLOBALS = [
    ("allocator_newex", 0xE85C0C),
    ("allocator_free",  0xE85C10),
    ("allocator_3",     0xE85C14),
    ("LSG_slot",        0x8269774),
    ("main_alloc",      0x84ABAD0),
    ("cfg_A",           0x81A76A8),
    ("cfg_B",           0x81A7F34),
    ("cfg_C",           0x81A9784),
]


def find_pid():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_client_shipRetail.exe",
                          "/FO", "CSV", "/NH"], capture_output=True, text=True,
                         errors="replace").stdout
    ps = []
    for line in out.splitlines():
        c = [x.strip('"') for x in line.split('","')]
        if len(c) >= 2 and c[0].lower() == "codomp_client_shipretail.exe":
            try:
                ps.append(int(c[1]))
            except ValueError:
                pass
    return ps


def rd(h, addr, n):
    b = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), b, n, ctypes.byref(got)):
        return None
    return b.raw[:got.value]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--secs", type=float, default=0)
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
        print("OpenProcess failed")
        return 2

    t0 = time.time()
    while True:
        print("--- t=%.1fs pid=%d ---" % (time.time() - t0, pid))
        for name, g in GLOBALS:
            raw = rd(h, g, 4)
            if raw is None:
                print("  %-16s 0x%08X = <read fail>" % (name, g))
                continue
            v = struct.unpack("<I", raw)[0]
            extra = ""
            if 0x400000 <= v < 0xE659000:
                s = rd(h, v, 32)
                if s:
                    extra = "  -> %r" % s.split(b"\x00")[0][:24]
            print("  %-16s 0x%08X = 0x%08X%s" % (name, g, v, extra))
        if a.secs <= 0 or time.time() - t0 >= a.secs:
            break
        time.sleep(3)
        if not find_pid():
            print("client exited")
            break
    k32.CloseHandle(h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
