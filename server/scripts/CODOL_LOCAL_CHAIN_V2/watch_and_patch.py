# -*- coding: utf-8 -*-
"""客户端一出现就打两个 patch，然后观察。

用法: python watch_and_patch.py
"""
import ctypes
import ctypes.wintypes as wt
import os
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
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualProtectEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                                 wt.DWORD, ctypes.POINTER(wt.DWORD)]


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


def rd(h, a, n):
    b = ctypes.create_string_buffer(n)
    g = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g)):
        return None
    return b.raw[:g.value]


def wr(h, a, data):
    old = wt.DWORD()
    if not k32.VirtualProtectEx(h, ctypes.c_void_p(a), len(data), 0x40, ctypes.byref(old)):
        return False
    g = ctypes.c_size_t()
    ok = k32.WriteProcessMemory(h, ctypes.c_void_p(a), data, len(data), ctypes.byref(g))
    k32.VirtualProtectEx(h, ctypes.c_void_p(a), len(data), old.value, ctypes.byref(wt.DWORD()))
    return bool(ok)


def main():
    t0 = time.time()
    done_pids = set()
    print("watching for client...", flush=True)
    try:
        while time.time() - t0 < 180:
            for cp in pids():
                if cp in done_pids:
                    continue
                h = k32.OpenProcess(PROC, False, cp)
                if not h:
                    continue
                # 等解壳：精度站点可读且匹配
                raw = rd(h, 0xC4A5D0, 10)
                if not raw or raw[:6] != bytes.fromhex("C785E8FDFFFF"):
                    k32.CloseHandle(h)
                    continue
                done_pids.add(cp)
                print("\n=== pid=%d 已解壳，打 patch ===" % cp, flush=True)

                imm = struct.unpack("<I", raw[6:10])[0]
                print("  精度站点 imm=%d" % imm, flush=True)
                if imm != 20:
                    wr(h, 0xC4A5D0, bytes.fromhex("C785E8FDFFFF") + struct.pack("<I", 20))
                    b = rd(h, 0xC4A5D0, 10)
                    print("  -> %s" % (b.hex(" ") if b else "?"), flush=True)

                for g, fn, name in [(0xE85C0C, 0xB78820, "new"),
                                    (0xE85C10, 0xB788D0, "free"),
                                    (0xE85C18, 0xB788A0, "delete")]:
                    wr(h, g, struct.pack("<I", fn))
                    b = rd(h, g, 4)
                    v = struct.unpack("<I", b)[0] if b else 0
                    print("  alloc[0x%08X] %-6s = 0x%08X %s"
                          % (g, name, v, "OK" if v == fn else "FAIL"), flush=True)
                wr(h, 0xE85C28, b"\x01")

                # 观察
                for k in range(25):
                    time.sleep(2)
                    if cp not in pids():
                        print("  t+%ds 退出" % ((k + 1) * 2), flush=True)
                        break
                    lsg = rd(h, 0x8269774, 4)
                    v = struct.unpack("<I", lsg)[0] if lsg else 0
                    print("  t+%2ds LSG=0x%08X" % ((k + 1) * 2, v), flush=True)
                k32.CloseHandle(h)
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
