# -*- coding: utf-8 -*-
"""专门抓 .tvm0 / .tls / .data 这些"模块映像区"(MEM_IMAGE)。

现有 _dump_mem_linear.py 用 MEM_PRIVATE 过滤, 会把 DLL 的映像节区
(.tvm0/.tls/.data 之类) 全部跳过 —— 所以资源表 0x239B120 抓不到。

本脚本: 用 nt10 早期句柄, 枚举 Base.dll 的映像区并把可读段 dump 出来。
必须走 elevated agent(或 nt10) 的早期句柄 —— ACE 生效后 VirtualQueryEx
对新开的句柄会拒绝。
"""
import ctypes
import os
import sys
import time
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
MEM_COMMIT = 0x1000
MEM_IMAGE = 0x1000000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
PAGE_READABLE = (0x02 | 0x04 | 0x10 | 0x20 | 0x40 | 0x80)
OUTDIR = os.path.dirname(os.path.abspath(__file__))


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


def dump_image_regions(h, outdir, min_rva=0x19DD000, max_rva=0x3940000,
                       log=print):
    """把模块映像区里 [min_rva, max_rva) 范围的可读段 dump 出来。

    min/max 用**虚拟地址**传入 —— 调用方给绝对地址。
    """
    os.makedirs(outdir, exist_ok=True)
    mbi = MEMORY_BASIC_INFORMATION()
    addr = min_rva
    total = 0
    n = 0
    t0 = time.time()
    while addr < max_rva:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                              ctypes.sizeof(mbi)) == 0:
            addr += 0x1000
            continue
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize or 0)
        if size <= 0:
            addr += 0x1000
            continue
        if (mbi.State == MEM_COMMIT
                and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))
                and (mbi.Protect & PAGE_READABLE)):
            fn = os.path.join(outdir, "r_%08X_%08X.bin" % (base, size))
            try:
                with open(fn, "wb") as f:
                    off = 0
                    while off < size:
                        want = int(min(0x400000, size - off))
                        d = rpm(h, base + off, want)
                        off += want
                        if not d:
                            break
                        f.write(d)
                        total += len(d)
                n += 1
            except Exception as e:
                log("  写 %s 失败: %r" % (fn, e))
        addr = base + size
    log("映像区 dump 完成: %d 个区, %.1f MB, 用时 %.1fs"
        % (n, total / 1048576.0, time.time() - t0))
    return n, total


def find_base_dll(handle, log=print):
    """找 Base.dll 的模块基址 —— 从 VirtualQueryEx 拿到的地址对照。"""
    # 先扫 0x10000000 附近(.tvm0 RVA 起点相对 ImageBase)
    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0x10000000
    for _ in range(200):
        if k32.VirtualQueryEx(handle, ctypes.c_void_p(addr),
                              ctypes.byref(mbi), ctypes.sizeof(mbi)) == 0:
            addr += 0x1000
            continue
        ab = int(mbi.AllocationBase or 0)
        if ab:
            log("  找到分配基址 0x%X (探针 @0x%X)" % (ab, addr))
            return ab
        addr += 0x10000
    return 0


def main():
    # 走 nt10 注入早期句柄: 直接从它传的 h 拿
    print("用法: 由 nt10 调用 dump_image_regions(h, outdir, base+tvm0_lo, base+tvm0_hi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
