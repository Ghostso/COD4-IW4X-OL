"""内存转储核心 —— 由提权 agent **在本进程内**执行（不开子进程，保住 SeDebugPrivilege）。

只读 ReadProcessMemory，不写目标进程。
用法（在提权进程里调用）:
    dump_client(outdir, max_mb)
"""
import ctypes
import ctypes.wintypes as wt
import os

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD), ("PartitionId", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
        ("szExeFile", wt.WCHAR * 260),
    ]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL

TARGET = "codoMP_client_shipRetail.exe"
PAGE_READABLE = (0x02 | 0x04 | 0x20 | 0x40 | 0x08 | 0x80)


def find_pids():
    h = k32.CreateToolhelp32Snapshot(2, 0)
    out = []
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32FirstW(h, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == TARGET.lower():
            out.append(int(e.th32ProcessID))
        ok = k32.Process32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return out


def readable(prot):
    if prot & 0x100 or prot & 0x01:
        return False
    return bool(prot & PAGE_READABLE)


def dump_client(outdir, max_mb=2048):
    lines = []
    pids = find_pids()
    if not pids:
        return ["客户端未运行"]
    pid = pids[0]
    lines.append("PID = %d" % pid)
    h = k32.OpenProcess(0x400 | 0x10, False, pid)
    if not h:
        return lines + ["OpenProcess 失败 err=%d" % ctypes.get_last_error()]

    os.makedirs(outdir, exist_ok=True)
    regions = []
    addr = 0
    while addr < 0x7FFF0000:
        mbi = MEMORY_BASIC_INFORMATION()
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                  ctypes.sizeof(mbi)):
            break
        size = int(mbi.RegionSize or 0)
        base = int(mbi.BaseAddress or 0)
        if mbi.State == 0x1000 and size > 0 and readable(mbi.Protect):
            regions.append((base, size, int(mbi.Protect), int(mbi.Type or 0)))
        addr = base + max(size, 1)

    total = sum(r[1] for r in regions)
    lines.append("可读区域 %d 个, 合计 %.1f MB" % (len(regions), total / 1048576))

    cap = max_mb * 1048576
    written = kept = 0
    CHUNK = 4 * 1048576            # 每次读 4MB, 避免一次性分配巨大缓冲
    first_err = None
    idx_path = os.path.join(outdir, "regions.txt")
    with open(idx_path, "w", encoding="utf-8") as idx:
        idx.write("# base size protect type file\n")
        for i, (base, size, prot, typ) in enumerate(regions):
            if written >= cap:
                idx.write("# 达到上限, 跳过其余 %d 个\n" % (len(regions) - i))
                break
            fname = "r_%08X.bin" % base
            got_total = 0
            fail_at = None
            with open(os.path.join(outdir, fname), "wb") as f:
                off = 0
                while off < size:
                    n = min(CHUNK, size - off)
                    buf = ctypes.create_string_buffer(n)
                    read = ctypes.c_size_t()
                    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base + off),
                                                 buf, n, ctypes.byref(read)):
                        err = ctypes.get_last_error()
                        if first_err is None:
                            first_err = (base + off, err)
                        fail_at = (off, err)
                        break
                    got = read.value
                    if got == 0:
                        break
                    f.write(buf.raw[:got])
                    got_total += got
                    off += got
            if got_total == 0:
                idx.write("# %08X READ_FAIL at=0x%X err=%s\n"
                          % (base, base, (fail_at[1] if fail_at else '?')))
                try:
                    os.remove(os.path.join(outdir, fname))
                except OSError:
                    pass
                continue
            idx.write("%08X %08X %08X %d %s%s\n"
                      % (base, got_total, prot, typ, fname,
                         "" if fail_at is None else " [partial]"))
            written += got_total
            kept += 1

    lines.append("首个读取错误: %r" % (first_err,))
    lines.append("写出 %d 个区域, %.1f MB" % (kept, written / 1048576))
    k32.CloseHandle(h)
    return lines
