# -*- coding: utf-8 -*-
"""实时采集客户端内存里的 SKU 目录记录(轻量, 不整片转储)。

记录布局(步长 0x60 = 96 字节, 实测于 mem_linear):
    +0x00 u32 sku
    +0x0C u32 (category/duration 类)
    +0x10 u32
    +0x14 u32 price
    +0x18 u32 0xFFFFFFFF
    +0x1C u32 0xFFFFFFFF

★ 用 nt10 的**早期句柄**(后开的会被 ACE 拒)。
  周期性扫, 每次把命中的 (sku, price) 并进结果文件。
  用于"在界面里翻页 -> 让客户端把更多条目加载进内存"的场景。
"""
import ctypes
import os
import struct
import time
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
STRIDE = 0x60
PRICE_NONE = 0xFFFFFFFF


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD), ("Protect", wintypes.DWORD),
                ("Type", wintypes.DWORD)]


k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                               ctypes.c_size_t]
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]


def rpm(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size,
                                 ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


def scan_buffer(b, found):
    n = 0
    limit = len(b) - STRIDE
    off = 0
    while off <= limit:
        sku = struct.unpack_from("<I", b, off)[0]
        if 100 <= sku <= 200000:
            a = struct.unpack_from("<I", b, off + 0x18)[0]
            if a == PRICE_NONE:
                c = struct.unpack_from("<I", b, off + 0x1C)[0]
                if c == PRICE_NONE:
                    price = struct.unpack_from("<I", b, off + 0x14)[0]
                    f0c = struct.unpack_from("<I", b, off + 0x0C)[0]
                    f10 = struct.unpack_from("<I", b, off + 0x10)[0]
                    # 只在"看起来像商品"时收录(价格合理)
                    if price != PRICE_NONE and price <= 5000000:
                        old = found.get(sku)
                        if old is None or (old[0] == PRICE_NONE and price != PRICE_NONE):
                            found[sku] = (price, f0c, f10)
                            n += 1
        off += 4
    return n


def scan_once(h):
    found = {}
    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0
    total = 0
    while addr < 0x7FFF0000:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                              ctypes.sizeof(mbi)) == 0:
            addr += 0x1000
            continue
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize or 0)
        if size <= 0:
            addr += 0x1000
            continue
        if (mbi.State == MEM_COMMIT and mbi.Type == MEM_PRIVATE
                and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))
                and size <= 256 * 1024 * 1024):
            off = 0
            while off < size:
                want = int(min(0x200000, size - off))
                d = rpm(h, base + off, want)
                off += want
                if not d:
                    continue
                total += len(d)
                scan_buffer(d, found)
        addr = base + size
    return found, total


def scan_loop(h, outdir, log, seconds=280.0, interval=20.0):
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "sku_live.txt")
    best = {}
    t0 = time.time()
    n = 0
    while time.time() - t0 < seconds:
        n += 1
        try:
            found, total = scan_once(h)
        except Exception as e:
            log("  [SKULIVE] 第 %d 轮异常: %r" % (n, e))
            found, total = {}, 0
        new = 0
        for k, v in found.items():
            if k not in best:
                new += 1
            best[k] = v
        # 落盘
        try:
            with open(out, "w", encoding="utf-8") as f:
                for k in sorted(best):
                    p, f0c, f10 = best[k]
                    f.write("%d\t%d\t%d\t%d\n" % (k, p, f0c, f10))
        except Exception:
            pass
        log("  [SKULIVE] 第 %d 轮: 本轮 %d, 新增 %d, 累计 %d (扫 %.1f MB)"
            % (n, len(found), new, len(best), total / 1048576.0))
        time.sleep(interval)
    log("  [SKULIVE] 结束, 累计 %d 条 -> %s" % (len(best), out))
    return best
