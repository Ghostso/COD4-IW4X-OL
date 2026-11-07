"""在游戏启动后**极早期**抢到进程句柄并保持, 之后再慢慢转储。

依据 nt10.py:2121-2122 的实测注释:
    # 早期句柄(实测它到 t=6s 仍可读写; 后开的会被 ACE 拒绝)
    h = k32.OpenProcess(PROC_ALL, False, pid)

PROC_ALL = 0x0008 | 0x0010 | 0x0020 | 0x0400
        = PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION

所以流程:
  1. 轮询等客户端进程出现
  2. **立刻** OpenProcess(PROC_ALL) 抢句柄
  3. 保持句柄不关, 等游戏初始化完
  4. 用这个早期句柄逐块读取全部可读区域
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

PROC_ALL = 0x0008 | 0x0010 | 0x0020 | 0x0400
TARGET = "codoMP_client_shipRetail.exe"


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


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wt.DWORD), ("HighPart", wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wt.DWORD),
                ("Privileges", LUID_AND_ATTRIBUTES * 1)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.GetCurrentProcess.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
# ★ 必须设 argtypes: 否则 64 位下 HANDLE 被按 32 位截断, GetCurrentProcess()
#   返回的伪句柄 (-1) 也会丢高位, OpenProcessToken 直接抛 ArgumentError。
advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
advapi32.OpenProcessToken.restype = wt.BOOL
advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                           ctypes.POINTER(LUID)]
advapi32.LookupPrivilegeValueW.restype = wt.BOOL
advapi32.AdjustTokenPrivileges.argtypes = [
    wt.HANDLE, wt.BOOL, ctypes.POINTER(TOKEN_PRIVILEGES), wt.DWORD,
    ctypes.c_void_p, ctypes.POINTER(wt.DWORD)]
advapi32.AdjustTokenPrivileges.restype = wt.BOOL

PAGE_READABLE = (0x02 | 0x04 | 0x20 | 0x40 | 0x08 | 0x80)


def enable_debug():
    k32.GetCurrentProcess.restype = wt.HANDLE
    tok = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(), 0x20 | 0x08,
                                     ctypes.byref(tok)):
        return False, ctypes.get_last_error()
    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(luid)):
        return False, ctypes.get_last_error()
    tp = TOKEN_PRIVILEGES()
    tp.PrivilegeCount = 1
    tp.Privileges[0].Luid = luid
    tp.Privileges[0].Attributes = 0x2
    ctypes.set_last_error(0)
    ok = advapi32.AdjustTokenPrivileges(tok, False, ctypes.byref(tp),
                                        ctypes.sizeof(tp), None, None)
    err = ctypes.get_last_error()
    k32.CloseHandle(tok)
    return bool(ok) and err == 0, err


def find_pid():
    h = k32.CreateToolhelp32Snapshot(2, 0)
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32FirstW(h, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == TARGET.lower():
            k32.CloseHandle(h)
            return int(e.th32ProcessID)
        ok = k32.Process32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return None


def readable(prot):
    if prot & 0x100 or prot & 0x01:
        return False
    return bool(prot & PAGE_READABLE)


def main():
    outdir = sys.argv[1]
    result_json = sys.argv[2]
    wait_init = float(sys.argv[3]) if len(sys.argv) > 3 else 40.0
    lines = []

    dbg, dbgerr = enable_debug()
    lines.append("SeDebugPrivilege = %s (err=%d)" % (dbg, dbgerr))

    # 1. 抢早期句柄
    pid = None
    h = None
    t0 = time.time()
    while time.time() - t0 < 600:
        p = find_pid()
        if p is not None:
            pid = p
            h = k32.OpenProcess(PROC_ALL, False, pid)
            if h:
                lines.append("抢到早期句柄 pid=%d handle=%s (t+%.1fs)"
                             % (pid, hex(h), time.time() - t0))
                break
            else:
                err = ctypes.get_last_error()
                lines.append("OpenProcess 失败 pid=%d err=%d" % (pid, err))
                h = None
                break
        time.sleep(0.15)

    if h is None:
        lines.append("未能取得进程句柄")
        json.dump({"ok": False, "lines": lines},
                  open(result_json, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        for ln in lines:
            print(ln)
        return 2

    # 2. 早读一次验证
    buf = ctypes.create_string_buffer(64)
    got = ctypes.c_size_t()
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(0x400000), buf, 64, ctypes.byref(got))
    lines.append("早读 0x400000 = %s (%s)"
                 % (ok, buf.raw[:16].hex() if ok else "err=%d" % ctypes.get_last_error()))

    # 3. 等游戏初始化
    lines.append("等待 %.0f 秒初始化..." % wait_init)
    time.sleep(wait_init)

    # 4. 枚举可读区域并用早期句柄读取
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
    lines.append("可读区域 %d 个, %.1f MB" % (len(regions), total / 1048576))

    written = kept = 0
    first_err = None
    CHUNK = 4 * 1048576
    idx_path = os.path.join(outdir, "regions.txt")
    with open(idx_path, "w", encoding="utf-8") as idx:
        idx.write("# base size protect type file\n")
        for base, size, prot, typ in regions:
            fname = "r_%08X.bin" % base
            got_total = 0
            with open(os.path.join(outdir, fname), "wb") as f:
                off = 0
                while off < size:
                    n = min(CHUNK, size - off)
                    b = ctypes.create_string_buffer(n)
                    rd = ctypes.c_size_t()
                    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base + off),
                                                 b, n, ctypes.byref(rd)):
                        if first_err is None:
                            first_err = (base + off, ctypes.get_last_error())
                        break
                    if rd.value == 0:
                        break
                    f.write(b.raw[:rd.value])
                    got_total += rd.value
                    off += rd.value
            if got_total == 0:
                idx.write("# %08X FAIL\n" % base)
                try:
                    os.remove(os.path.join(outdir, fname))
                except OSError:
                    pass
                continue
            idx.write("%08X %08X %08X %d %s\n" % (base, got_total, prot, typ, fname))
            written += got_total
            kept += 1

    lines.append("首个错误: %r" % (first_err,))
    lines.append("写出 %d 个区域, %.1f MB" % (kept, written / 1048576))
    k32.CloseHandle(h)
    json.dump({"ok": kept > 0, "lines": lines},
              open(result_json, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    for ln in lines:
        print(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
