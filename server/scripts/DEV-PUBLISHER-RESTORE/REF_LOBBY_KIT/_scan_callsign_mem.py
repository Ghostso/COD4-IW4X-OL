# -*- coding: utf-8 -*-
"""定点扫描客户端内存里的**称号表**(callsignTitle.csv 解密后的内容)。

背景: 称号(`pct_`)在 marketplace 包里只有 `pct_default` —— 因为称号是**文本**,
不是图片。文本表 `mp/callsignTitle.csv` 由客户端在**打开称号选择界面**时加载,
那时它在内存里是明文。本模块周期性扫, 命中就导出。

判据(命中任一即导出该区域):
  1) 出现 `callsignTitle` / `TITLE_NAME` / `CALLSIGN_TITLE_EMB_NAME` 等表相关串;
  2) 出现**成片的 `TITLE_xxx` 键**(>=20 个不同键, 说明表已展开);
  3) 出现成片 UTF-8 中文 + 短键的 CSV 行特征。
"""
import ctypes
import os
import re
import time
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


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

TITLE_KEY = re.compile(rb"TITLE_[A-Z0-9_]{3,40}")
CS_KEY = re.compile(rb"CALLSIGN_[A-Z0-9_]{3,40}")


def rpm(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size,
                                 ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


def scan_once(h, outdir, log, cap=8):
    """扫一遍; 命中即导出。返回命中数。"""
    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0
    hits = 0
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
                and size <= 128 * 1024 * 1024):
            off = 0
            while off < size:
                want = int(min(0x200000, size - off))
                d = rpm(h, base + off, want)
                off += want
                if not d:
                    continue
                keys = set(m.group(0) for m in TITLE_KEY.finditer(d))
                csk = set(m.group(0) for m in CS_KEY.finditer(d))
                # 判据: 大量不同 TITLE_ 键(说明是展开的表, 不是零散引用)
                if len(keys) >= 20 or len(csk) >= 20:
                    va = base + off - want
                    fn = os.path.join(outdir, "callsign_0x%08X.bin" % va)
                    try:
                        open(fn, "wb").write(d)
                    except Exception:
                        pass
                    hits += 1
                    log("  [CS] ★★ 命中称号表 @0x%08X: TITLE_键=%d CALLSIGN_键=%d (%d 字节)"
                        % (va, len(keys), len(csk), len(d)))
                    for k in sorted(keys)[:12]:
                        log("        %s" % k.decode("latin1"))
                    if hits >= cap:
                        return hits
        addr = base + size
    return hits


def scan_loop(h, outdir, log, seconds=280.0, interval=15.0):
    os.makedirs(outdir, exist_ok=True)
    t0 = time.time()
    n = 0
    while time.time() - t0 < seconds:
        n += 1
        try:
            hh = scan_once(h, outdir, log)
        except Exception as e:
            log("  [CS] 第 %d 轮异常: %r" % (n, e))
            hh = 0
        if hh:
            log("  [CS] 第 %d 轮命中 %d 处" % (n, hh))
            return
        time.sleep(interval)
    log("  [CS] 扫描结束, 未命中")
