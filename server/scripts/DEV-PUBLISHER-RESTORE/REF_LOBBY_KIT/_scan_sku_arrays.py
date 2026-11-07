# -*- coding: utf-8 -*-
"""在运行中的客户端里找"SKU/目录记录数组"。

已知线索(见 HANDOFF_20261005_LOBBY_BUGS.md §4.0):
  · 客户端购买帧里的 sku = 241/242/31774/31816 → 来自它**自己那份**目录;
  · 离线转储里发现 48 字节定长、id 连续递增的记录池(31769→31774→31780)。

本扫描器要的是**结构化的目录记录**: 连续 N 条 48B 记录, 首字段是递增的 id,
且非首字段里出现"像价格"的小整数(几百~几百万)。

★ 用 nt10 的早期句柄跑(后开的句柄会被 ACE 拒), 见 nt10.py:1888。
"""
import argparse
import ctypes
import os
import struct
import sys
import time
from ctypes import wintypes

OUTDIR = os.path.dirname(os.path.abspath(__file__))

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = -1
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
MEM_PRIVATE = 0x20000


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_char * 260)]


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
k32.OpenProcess.restype = wintypes.HANDLE


def find_pid_by_name(name):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == INVALID_HANDLE_VALUE:
        return None
    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
    try:
        ok = k32.Process32First(snap, ctypes.byref(pe))
        while ok:
            exe = pe.szExeFile.decode("latin1", "replace").lower()
            if exe in (name.lower(), name.lower() + ".exe"):
                return int(pe.th32ProcessID)
            ok = k32.Process32Next(snap, ctypes.byref(pe))
    finally:
        k32.CloseHandle(snap)
    return None


def rpm(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size,
                                 ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


def find_arrays(d, stride_hint=48, min_run=24):
    """在数据里找"定长记录、首字段递增且互不重复"的连续段。返回 [(off, stride, n, ids)]。

    ★ 与第一版的差别(2026-10-05 教训): 第一版只要求"非递减", 结果把
      纹理/像素数据(一整片相同的 3763 / 1024)也当成目录。真正的商品目录
      特征是 **id 严格递增且基本互不重复**。
    """
    found = []
    n = len(d)
    for stride in (stride_hint, 24, 32, 40, 56, 64, 72):
        for phase in range(stride):
            run_start = None
            run_ids = []
            off = phase
            while off + 4 <= n:
                v = struct.unpack_from("<I", d, off)[0]
                ok = (100 <= v <= 500000) and (not run_ids or v > run_ids[-1])
                if ok:
                    if not run_ids:
                        run_start = off
                    run_ids.append(v)
                else:
                    if len(run_ids) >= min_run and _is_catalog_like(run_ids):
                        found.append((run_start, stride, len(run_ids), list(run_ids)))
                    run_ids = []
                off += stride
            if len(run_ids) >= min_run and _is_catalog_like(run_ids):
                found.append((run_start, stride, len(run_ids), list(run_ids)))
    return found


def _is_catalog_like(ids):
    """目录 vs 像素/结构数据的判别: id 必须严格递增, 且去重率高、跨度合理。"""
    if len(ids) < 24:
        return False
    if len(set(ids)) < len(ids) * 0.95:      # 几乎全不重复
        return False
    span = ids[-1] - ids[0]
    if span <= 0 or span > 400000:
        return False
    return True


def scan_marketplace_sku_arrays(h, log, seconds=90.0, min_run=24, cap=40):
    """供 nt10 调用的扫描入口: 用**已持有的句柄** h 扫 SKU/目录记录数组。

    返回 [(va, stride, n, ids)]。只导出"像目录"的段到 sku_arrays\。
    """
    out = os.path.join(OUTDIR, "sku_arrays")
    try:
        os.makedirs(out, exist_ok=True)
    except Exception:
        pass
    mbi = MEMORY_BASIC_INFORMATION()
    t0 = time.time()
    addr = 0
    results = []
    dumped = 0
    total = 0
    while addr < 0x7FFF0000 and time.time() - t0 < seconds:
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
                and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))):
            off = 0
            while off < size:
                want = int(min(0x200000, size - off))
                d = rpm(h, base + off, want)
                off += want
                if not d:
                    continue
                total += len(d)
                for aoff, stride, n, ids in find_arrays(d, min_run=min_run):
                    va = base + off - want + aoff
                    results.append((va, stride, n, ids))
                    if dumped < cap:
                        chunk = rpm(h, max(0x1000, va - 0x1000),
                                    min(0x200000, n * stride + 0x2000))
                        if chunk:
                            fn = os.path.join(out, "arr_0x%08X_s%d_n%d.bin"
                                              % (va, stride, n))
                            try:
                                open(fn, "wb").write(chunk)
                                dumped += 1
                            except Exception:
                                pass
        addr = base + size
    if results:
        log("  [SKU] 扫描 %.1f MB -> %d 个目录候选(导出 %d)"
            % (total / 1048576.0, len(results), dumped))
        for va, stride, n, ids in results[:12]:
            log("        base=0x%08X stride=%d n=%d ids=%s" % (va, stride, n, ids[:6]))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="codoMP_client_shipRetail")
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--min-run", type=int, default=24)
    a = ap.parse_args()

    pid = a.pid or find_pid_by_name(a.name)
    if not pid:
        print("找不到进程 %s" % a.name)
        return 1
    print("pid = %d" % pid)
    h = k32.OpenProcess(0x1F0FFF, False, pid)
    if not h:
        print("OpenProcess 失败 err=%d (需提权; 且需早期句柄)" % ctypes.get_last_error())
        return 1
    probe = MEMORY_BASIC_INFORMATION()
    if k32.VirtualQueryEx(h, ctypes.c_void_p(0x400000), ctypes.byref(probe),
                          ctypes.sizeof(probe)) == 0:
        print("VirtualQueryEx 失败 err=%d —— 句柄太晚(ACE 已生效)"
              % ctypes.get_last_error())
        return 2

    out = os.path.join(OUTDIR, "sku_arrays")
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
    total = 0
    dumped = 0
    while addr < 0x7FFF0000 and time.time() - t0 < a.seconds:
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
                and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))):
            off = 0
            while off < size:
                want = int(min(0x200000, size - off))
                d = rpm(h, base + off, want)
                off += want
                if not d:
                    continue
                total += len(d)
                arrs = find_arrays(d, min_run=a.min_run)
                for aoff, stride, n, ids in arrs:
                    va = base + off - want + aoff
                    print("  ★ 数组 base=0x%08X stride=%d n=%d ids[0..6]=%s"
                          % (va, stride, n, ids[:6]))
                    if dumped < 40:
                        chunk = rpm(h, max(0x1000, va - 0x1000),
                                    min(0x200000, n * stride + 0x2000))
                        if chunk:
                            fn = os.path.join(out, "arr_0x%08X_s%d_n%d.bin"
                                              % (va, stride, n))
                            open(fn, "wb").write(chunk)
                            dumped += 1
        addr = base + size
    print("扫描 %.1f MB, 导出 %d 个数组, 用时 %.1fs"
          % (total / 1048576.0, dumped, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
