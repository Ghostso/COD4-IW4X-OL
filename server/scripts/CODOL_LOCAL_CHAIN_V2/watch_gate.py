# -*- coding: utf-8 -*-
"""读 bdNet 启动门 [0xE59D20] 的实时状态。

已知：值 4 或 6 才会调用 GetLSG 创建 LSG 对象。
      该门在等 UDP:3074 的 DW NAT 发现。
"""
import ctypes
import ctypes.wintypes as wt
import struct
import subprocess
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

WATCH = [
    ("bdNet_gate", 0xE59D20),
    ("flag_84abacc", 0x84ABACC),
    ("flag_82ca046", 0x82CA046),
    ("LSG_slot", 0x8269774),
]


def pids():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_client_shipRetail.exe",
                          "/FO", "CSV", "/NH"], capture_output=True, text=True,
                         errors="replace").stdout
    r = []
    for line in out.splitlines():
        c = [x.strip('"') for x in line.split('","')]
        if len(c) >= 2 and c[0].lower() == "codomp_client_shipretail.exe":
            try:
                r.append(int(c[1]))
            except ValueError:
                pass
    return r


def main():
    t0 = time.time()
    seen = set()
    while time.time() - t0 < 120:
        for cp in pids():
            if cp in seen:
                continue
            h = k32.OpenProcess(0x0410, False, cp)
            if not h:
                continue
            seen.add(cp)
            print("\n=== pid=%d ===" % cp, flush=True)
            for k in range(30):
                time.sleep(1)
                if cp not in pids():
                    print("  t+%ds 退出" % (k + 1), flush=True)
                    break
                vals = []
                for name, g in WATCH:
                    b = ctypes.create_string_buffer(4)
                    got = ctypes.c_size_t()
                    if k32.ReadProcessMemory(h, ctypes.c_void_p(g), b, 4, ctypes.byref(got)):
                        v = struct.unpack("<I", b.raw[:4])[0]
                        vals.append("%s=0x%X" % (name, v))
                    else:
                        vals.append("%s=?" % name)
                print("  t+%2ds %s" % (k + 1, "  ".join(vals)), flush=True)
            k32.CloseHandle(h)
        time.sleep(0.3)
    return 0


if __name__ == "__main__":
    sys.exit(main())
