# -*- coding: utf-8 -*-
"""扫描客户端内存里的 80/70 探针哨兵。

market_sku_probe.py 往 80/70 应答里填了唯一常量:
    name="PROBE0"  id=0x11111111  productId=0x22222222
    originalPrice=0x33333333  price=0x44444444  currency=0x55
客户端**解析成功**时, 这些值会被写进它构造的 SKUObj 并留在内存里。
命中 = 该线格式被客户端接受; 全不命中 = 解析失败/被拒。

由 nt10 用早期句柄周期调用。也支持离线扫转储目录:
    python _scan_probe_sentinels.py mem_linear
"""
import ctypes
import os
import struct
import sys
import time

SENTINELS = {
    "name": (b"PROBE0", "PROBE0"),
    "id": (struct.pack("<I", 0x11111111), "0x11111111"),
    "productId": (struct.pack("<I", 0x22222222), "0x22222222"),
    "originalPrice": (struct.pack("<I", 0x33333333), "0x33333333"),
    "price": (struct.pack("<I", 0x44444444), "0x44444444"),
}

CHUNK = 8 * 1024 * 1024


def scan_buffer(buf, base, hits, log=None, max_per_key=8):
    for key, (pat, label) in SENTINELS.items():
        i = buf.find(pat)
        while i >= 0:
            lst = hits.setdefault(key, [])
            if len(lst) < max_per_key:
                lst.append((base + i, label))
                if log:
                    log("  [PROBE] ★ 哨兵 %s (%s) @0x%08X" % (key, label, base + i))
            i = buf.find(pat, i + 1)


def scan_dir(d, hits=None, log=print):
    hits = hits if hits is not None else {}
    for fn in sorted(os.listdir(d)):
        p = os.path.join(d, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        base = 0
        if fn.startswith("r_") and fn.endswith(".bin"):
            try:
                base = int(fn.split("_")[1], 16)
            except Exception:
                base = 0
        scan_buffer(b, base, hits, log=log)
    return hits


def scan_live_once(h, k32, log=print, hits=None):
    from ctypes import wintypes

    class MBI(ctypes.Structure):
        _fields_ = [("BaseAddress", ctypes.c_void_p),
                    ("AllocationBase", ctypes.c_void_p),
                    ("AllocationProtect", wintypes.DWORD),
                    ("RegionSize", ctypes.c_size_t),
                    ("State", wintypes.DWORD), ("Protect", wintypes.DWORD),
                    ("Type", wintypes.DWORD)]

    hits = hits if hits is not None else {}
    mbi = MBI()
    addr = 0
    while addr < 0x7FFF0000:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                              ctypes.sizeof(mbi)) == 0:
            addr += 0x1000
            continue
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize or 0)
        if (mbi.State == 0x1000 and (mbi.Protect & 0xEE)
                and not (mbi.Protect & 0x101) and 0 < size <= 512 * 1024 * 1024):
            off = 0
            while off < size:
                want = int(min(CHUNK, size - off))
                buf = ctypes.create_string_buffer(want)
                got = ctypes.c_size_t(0)
                if k32.ReadProcessMemory(h, ctypes.c_void_p(base + off), buf,
                                         want, ctypes.byref(got)) and got.value:
                    scan_buffer(buf.raw[:got.value], base + off, hits, log=log)
                off += want
        addr = base + size
    return hits


def scan_live_thread(h, log=print, seconds=280.0, interval=15.0):
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    hits = {}
    t0 = time.time()
    n = 0
    while time.time() - t0 < seconds:
        n += 1
        before = sum(len(v) for v in hits.values())
        try:
            scan_live_once(h, k32, log=log, hits=hits)
        except Exception as e:
            log("  [PROBE] 第 %d 轮异常: %r" % (n, e))
        after = sum(len(v) for v in hits.values())
        log("  [PROBE] 第 %d 轮: 哨兵累计 %d 处 %s"
            % (n, after, "★ 新增 %d" % (after - before) if after > before else ""))
        if after:
            break
        time.sleep(interval)
    return hits


if __name__ == "__main__":
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        h = scan_dir(sys.argv[1])
        print("哨兵命中:", {k: v[:3] for k, v in h.items()})
    else:
        print(__doc__)
