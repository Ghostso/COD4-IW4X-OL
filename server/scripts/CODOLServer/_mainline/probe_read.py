"""最小化诊断: 尝试读取游戏进程的几个已知地址, 打印详细错误。

排除"批量读取的缓冲/参数问题", 只看单次 ReadProcessMemory 是否可行。
用法（管理员）: python -I probe_read.py <result_json>
"""
import ctypes
import ctypes.wintypes as wt
import json
import sys

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
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t

advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wt.DWORD), ("HighPart", wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wt.DWORD),
                ("Privileges", LUID_AND_ATTRIBUTES * 1)]


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
        if e.szExeFile.lower() == "codomp_client_shipretail.exe":
            k32.CloseHandle(h)
            return int(e.th32ProcessID)
        ok = k32.Process32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return None


out = []
dbg_ok, dbg_err = enable_debug()
out.append("SeDebugPrivilege 启用 = %s (err=%d)" % (dbg_ok, dbg_err))

pid = find_pid()
out.append("客户端 PID = %r" % (pid,))
if pid is None:
    json.dump({"ok": False, "lines": out}, open(sys.argv[1], "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    sys.exit(2)

# 尝试不同权限组合
for name, access in [("QUERY|VM_READ", 0x400 | 0x10),
                     ("ALL_ACCESS", 0x1F0FFF),
                     ("QUERY|VM_READ|VM_WRITE|VM_OP", 0x400 | 0x10 | 0x20 | 0x8)]:
    h = k32.OpenProcess(access, False, pid)
    if not h:
        out.append("OpenProcess(%s) 失败 err=%d" % (name, ctypes.get_last_error()))
        continue
    out.append("OpenProcess(%s) OK handle=%s" % (name, hex(h)))

    # 读游戏主模块
    for addr in (0x400000, 0x401000, 0x714000):
        buf = ctypes.create_string_buffer(64)
        read = ctypes.c_size_t()
        ok = k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, 64, ctypes.byref(read))
        if ok:
            out.append("  read 0x%X OK %d 字节: %s"
                       % (addr, read.value, buf.raw[:16].hex()))
        else:
            out.append("  read 0x%X FAIL err=%d" % (addr, ctypes.get_last_error()))
    k32.CloseHandle(h)
    break

json.dump({"ok": True, "lines": out}, open(sys.argv[1], "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
for ln in out:
    print(ln)
