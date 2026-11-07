# -*- coding: utf-8 -*-
"""在运行中的客户端里找 common_marketplace_lite 的**已解密**副本。

背景:
  common_marketplace_lite.ff 的层二(引擎自有加密)静态无法解(见
  HANDOFF_20261005_LOBBY_BUGS.md §4.0.1~4.0.2)。但客户端启动时必然把它
  解密后放进内存, 于是内存里存在明文副本 —— 这里去捞它。

锚点(按可靠性排序):
  1) 'common_marketplace_lite'   zone 名(层一里就在 +0x12C)
  2) 'IWffs100'                  容器魔数
  3) 'common_marketplace_lite1'  另一个市场包

用法(需提权, 因为客户端被 TP3/ACE 加壳):
  python -X utf8 _scan_marketplace_mem.py --pid <pid> [--out mem_dump]
  python -X utf8 _scan_marketplace_mem.py --name codoMP_client_shipRetail
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

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
# ★ nt10.py 的经验(见 nt10.py:1888 注释): 客户端被 ACE/TP3 保护, **后开的句柄会被拒绝**;
#   只有在进程**刚启动、保护尚未生效**时拿到句柄才能读。nt10.py 用的是 PROC_ALL。
PROCESS_ALL = 0x1F0FFF
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
INVALID_HANDLE_VALUE = -1

MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_char * 260)]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD),
                ("Protect", wintypes.DWORD),
                ("Type", wintypes.DWORD)]


k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                               ctypes.c_size_t]
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]


def find_pid_by_name(name):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == INVALID_HANDLE_VALUE:
        return None
    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
    try:
        ok = k32.Process32First(snap, ctypes.byref(pe))
        while ok:
            exe = pe.szExeFile.decode("latin1", "replace")
            if exe.lower() == name.lower() or \
                    exe.lower() == (name.lower() + ".exe"):
                return int(pe.th32ProcessID)
            ok = k32.Process32Next(snap, ctypes.byref(pe))
    finally:
        k32.CloseHandle(snap)
    return None


def rpm(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size,
                               ctypes.byref(got))
    if not ok:
        return None
    return buf.raw[:got.value]


def regions(h):
    """遍历所有可读的已提交区, 产出 (base, size, protect, type)。"""
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()
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
        if (mbi.State == MEM_COMMIT
                and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))):
            yield base, size, int(mbi.Protect), int(mbi.Type)
        addr = base + size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--name", default="codoMP_client_shipRetail")
    ap.add_argument("--out", default=os.path.join(OUTDIR, "mem_marketplace"))
    ap.add_argument("--max-region", type=int, default=64 * 1024 * 1024,
                    help="单个区最大读取字节")
    ap.add_argument("--dump-window", type=int, default=1 * 1024 * 1024,
                    help="命中点附近导出多少字节")
    a = ap.parse_args()

    pid = a.pid or find_pid_by_name(a.name)
    if not pid:
        print("找不到进程 %s" % a.name)
        return 1
    print("pid = %d" % pid)

    h = k32.OpenProcess(PROCESS_ALL, False, pid)
    if not h:
        # 退回最小权限再试一次
        h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print("OpenProcess 失败 err=%d (需要提权)" % ctypes.get_last_error())
        return 1
    # ★ 先探测一次 VirtualQueryEx: 在启用 ACE/TP3 的进程上, 即便 OpenProcess
    #   成功, VirtualQueryEx 也可能返回 0/err=5(拒绝访问)。这时下面遍历会是空,
    #   必须显式报出来, 否则"扫描 0.0 MB"会被误读成"内存里没有"。
    mbi_probe = MEMORY_BASIC_INFORMATION()
    if k32.VirtualQueryEx(h, ctypes.c_void_p(0x400000),
                          ctypes.byref(mbi_probe),
                          ctypes.sizeof(mbi_probe)) == 0:
        print("VirtualQueryEx 失败 err=%d —— 进程受保护(ACE/TP3), 无法遍历内存。"
              % ctypes.get_last_error())
        print("提示: 必须在客户端**刚启动、保护尚未生效**的窗口内取句柄并保持")
        print("      (nt10.py:1888 实测: 早期句柄到 t=6s 仍可读写, 后开的会被拒绝)。")
        print("      对策: 把本扫描并进 nt10 的早期句柄流程, 而不是事后另开句柄。")
        k32.CloseHandle(h)
        return 2

    anchors = [b"common_marketplace_lite", b"IWffs100",
               b"common_marketplace_lite1"]
    hits = {k: [] for k in anchors}
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    total = 0
    dumped = 0

    for base, size, prot, typ in regions(h):
        off = 0
        while off < size:
            want = int(min(0x100000, size - off, max(0, a.max_region - off)))
            if want <= 0:
                break
            d = rpm(h, base + off, want)
            off += want
            if not d:
                continue
            total += len(d)
            for k in anchors:
                pos = d.find(k)
                while pos >= 0:
                    va = base + off - want + pos
                    hits[k].append(va)
                    if dumped < 12:
                        w = a.dump_window
                        start = max(base + off - want, va - w // 2)
                        chunk = rpm(h, start, w)
                        if chunk:
                            fn = os.path.join(
                                a.out, "hit_%02d_0x%08X_%s.bin"
                                % (dumped, va, k.decode("latin1", "replace")[:12]))
                            open(fn, "wb").write(chunk)
                            dumped += 1
                    pos = d.find(k, pos + 1)
        if time.time() - t0 > 240:
            print("超时保护: 已扫描 %.1f MB" % (total / 1048576.0))
            break

    print("扫描 %.1f MB, 用时 %.1fs" % (total / 1048576.0, time.time() - t0))
    for k in anchors:
        vs = hits[k]
        print("  %-28s 命中 %d 处%s"
              % (k.decode("latin1", "replace"), len(vs),
                 ("  " + ", ".join("0x%08X" % v for v in vs[:8])) if vs else ""))
    print("导出目录: %s (%d 个窗口)" % (a.out, dumped))
    k32.CloseHandle(h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
