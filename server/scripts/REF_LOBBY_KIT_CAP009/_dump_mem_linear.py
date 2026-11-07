# -*- coding: utf-8 -*-
"""对客户端做**整片线性**内存转储(每个可读私有区只导一次, 不重叠)。

★ 为什么不用之前那版: `marketplace_mem_scan_thread` 是"每个命中点前后各 1MB",
  14017 个命中互相重叠 -> 9.5GB 里绝大部分是重复数据。
  线性版每个区只读写一遍, 同样覆盖全部内存, 体积小得多。

用途: 进大厅并**打开商城**后跑一次, 然后离线用已知 SKU 号
(31774/31816/32223 等) 和价格去定位客户端的 SKU 目录实例。

必须在 nt10 的**早期句柄**下跑(ACE 生效后 VirtualQueryEx 会被拒)。
"""
import ctypes
import os
import sys
import time
from ctypes import wintypes

OUTDIR = os.path.dirname(os.path.abspath(__file__))

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = -1
MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
MEM_IMAGE = 0x1000000
MEM_MAPPED = 0x40000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
PAGE_READABLE = (0x02 | 0x04 | 0x10 | 0x20 | 0x40 | 0x80)


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


def dump_all(h, outdir, budget_mb=3000, log=print):
    os.makedirs(outdir, exist_ok=True)
    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0
    total = 0
    files = 0
    t0 = time.time()
    budget = budget_mb * 1024 * 1024
    while addr < 0x7FFF0000 and total < budget:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                              ctypes.sizeof(mbi)) == 0:
            addr += 0x1000
            continue
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize or 0)
        if size <= 0:
            addr += 0x1000
            continue
        # ★ 2026-10-06: 原过滤条件只有 MEM_PRIVATE, 会把**模块映像区**
        #   (.tvm0/.tls/.data 这类 DLL 节区) 全部跳过 ——
        #   资源注册表 0x239B120 因此一直抓不到(它就在 Base.dll 的 .tvm0)。
        #   现在: MEM_PRIVATE 和 MEM_IMAGE 都收, 但跳过 MEM_MAPPED(文件映射)。
        #   可读性再按 protect 判, 不再只看 Type。
        is_private = (mbi.Type == MEM_PRIVATE)
        is_image = (mbi.Type == MEM_IMAGE)
        readable = bool(mbi.Protect & PAGE_READABLE)
        if (mbi.State == MEM_COMMIT and (is_private or is_image)
                and readable
                and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))
                and size <= 512 * 1024 * 1024):
            fn = os.path.join(outdir, "r_%08X_%08X.bin" % (base, size))
            try:
                with open(fn, "wb") as f:
                    off = 0
                    while off < size and total < budget:
                        want = int(min(0x400000, size - off))
                        d = rpm(h, base + off, want)
                        off += want
                        if not d:
                            break
                        f.write(d)
                        total += len(d)
                files += 1
            except Exception as e:
                log("  写 %s 失败: %r" % (fn, e))
        addr = base + size
    log("线性转储完成: %d 个区, %.2f GB, 用时 %.1fs"
        % (files, total / 1073741824.0, time.time() - t0))
    return files, total


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "codoMP_client_shipRetail"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUTDIR, "mem_linear")
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
    pid = find_pid_by_name(name)
    if not pid:
        print("找不到进程 %s" % name)
        return 1
    print("pid = %d" % pid)
    h = k32.OpenProcess(0x1F0FFF, False, pid)
    if not h:
        print("OpenProcess 失败 err=%d" % ctypes.get_last_error())
        return 1
    probe = MEMORY_BASIC_INFORMATION()
    if k32.VirtualQueryEx(h, ctypes.c_void_p(0x400000), ctypes.byref(probe),
                          ctypes.sizeof(probe)) == 0:
        print("VirtualQueryEx 失败 err=%d (句柄太晚)" % ctypes.get_last_error())
        return 2
    dump_all(h, out, budget)
    return 0


if __name__ == "__main__":
    sys.exit(main())
