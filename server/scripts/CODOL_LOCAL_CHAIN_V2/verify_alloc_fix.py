# -*- coding: utf-8 -*-
"""独立验证：起客户端 -> 打两个 patch -> 持续观察 LSG 槽。

不依赖 run_all，直接操作，避免输出缓冲干扰。
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

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_LOCAL_CHAIN_V2"
GAME = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL"
PY = sys.executable


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
    # 1. 起链
    env = dict(os.environ, OLMOD_GAME_ROOT=GAME)
    log = open(os.path.join(ROOT, "_verify_chain.log"), "w")
    p = subprocess.Popen([PY, "-u", "run_all.py", "--secs", "120", "--retries", "1",
                          "--out", "_V.txt"], cwd=ROOT, env=env,
                       stdout=log, stderr=subprocess.STDOUT)
    print("chain pid=%d" % p.pid)

    # 2. 等客户端
    cp = 0
    for _ in range(120):
        time.sleep(0.5)
        ps = pids()
        if ps:
            cp = max(ps)
            break
    if not cp:
        print("!! no client")
        return 2
    print("client pid=%d" % cp)

    h = k32.OpenProcess(PROC, False, cp)
    if not h:
        print("!! OpenProcess failed")
        return 2

    time.sleep(10)  # 等解壳

    # 3. patch 精度
    raw = rd(h, 0xC4A5D0, 10)
    print("精度站点: %s" % (raw.hex(" ") if raw else "?"))
    if raw and raw[:6] == bytes.fromhex("C785E8FDFFFF"):
        wr(h, 0xC4A5D0, bytes.fromhex("C785E8FDFFFF") + struct.pack("<I", 20))
        back = rd(h, 0xC4A5D0, 10)
        print("精度 patch -> %s" % (back.hex(" ") if back else "?"))

    # 4. 装分配器
    for g, fn, name in [(0xE85C0C, 0xB78820, "new"),
                        (0xE85C10, 0xB788D0, "free"),
                        (0xE85C18, 0xB788A0, "delete")]:
        wr(h, g, struct.pack("<I", fn))
        back = rd(h, g, 4)
        v = struct.unpack("<I", back)[0] if back else 0
        print("  [0x%08X] %-6s -> 0x%08X %s" % (g, name, v, "OK" if v == fn else "FAIL"))
    wr(h, 0xE85C28, b"\x01")

    # 5. 持续观察
    print()
    print("=== 观察 LSG 槽（每 2 秒）===")
    for k in range(20):
        time.sleep(2)
        if cp not in pids():
            print("t+%ds 客户端退出" % ((k + 1) * 2))
            break
        lsg = rd(h, 0x8269774, 4)
        v = struct.unpack("<I", lsg)[0] if lsg else 0
        flag = rd(h, 0xE85C28, 1)
        print("t+%2ds LSG=0x%08X flag=%s" % ((k + 1) * 2, v,
                                             flag.hex() if flag else "?"))

    k32.CloseHandle(h)
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
