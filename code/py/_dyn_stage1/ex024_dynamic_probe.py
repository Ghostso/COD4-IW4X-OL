import ctypes
import ctypes.wintypes as wt
import datetime as dt
import os
import sys
import time

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
WEGAME = os.path.join(ROOT, "WeGame")
TGP = os.path.join(WEGAME, "tgp_daemon.exe")
CMD = (
    '"' + TGP + '" -launcher={"ad_begin":"","ad_end":"","ad_path":"D:\\\\BaiduNetdiskDownload\\\\使命召唤OL\\\\COD OL\\\\WeGameLauncher\\\\game\\\\ad_login.png","ad_type":1,"ad_url":"http://codol.qq.com/","ad_video":"D:\\\\BaiduNetdiskDownload\\\\使命召唤OL\\\\COD OL\\\\WeGameLauncher\\\\game\\\\ad_mini.mp4","click_btn_show_txt":"查看详情","custom":"26","game_id":29,"launcher_ver":"1.3.0.76"}  StartFor=29 AddPath="D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL"'
)
DURATION = 35

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
        ("szExeFile", wt.WCHAR * 260),
    ]


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [("Length", wt.USHORT), ("MaximumLength", wt.USHORT), ("Buffer", ctypes.c_void_p)]


class OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Length", wt.ULONG), ("RootDirectory", wt.HANDLE), ("ObjectName", ctypes.POINTER(UNICODE_STRING)),
        ("Attributes", wt.ULONG), ("SecurityDescriptor", ctypes.c_void_p), ("SecurityQualityOfService", ctypes.c_void_p),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD), ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD), ("dwFlags", wt.DWORD),
        ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD), ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wt.HANDLE), ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE), ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]


class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD), ("fMask", wt.ULONG), ("hwnd", wt.HWND),
        ("lpVerb", wt.LPCWSTR), ("lpFile", wt.LPCWSTR), ("lpParameters", wt.LPCWSTR),
        ("lpDirectory", wt.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wt.HANDLE),
        ("lpIDList", ctypes.c_void_p), ("lpClass", wt.LPCWSTR), ("hkeyClass", wt.HANDLE),
        ("dwHotKey", wt.DWORD), ("hIcon", wt.HANDLE), ("hProcess", wt.HANDLE),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD), ("PartitionId", wt.DWORD), ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD),
    ]


k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
k32.CreateProcessW.restype = wt.BOOL
k32.GetProcessId.argtypes = [wt.HANDLE]
k32.GetProcessId.restype = wt.DWORD
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
shell32.ShellExecuteExW.restype = wt.BOOL
k32.OpenFileMappingW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
k32.OpenFileMappingW.restype = wt.HANDLE
k32.MapViewOfFile.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD, wt.DWORD, ctypes.c_size_t]
k32.MapViewOfFile.restype = ctypes.c_void_p
k32.VirtualQuery.argtypes = [ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.VirtualQuery.restype = ctypes.c_size_t
k32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
k32.GetCurrentProcessId.argtypes = []
k32.GetCurrentProcessId.restype = wt.DWORD
k32.ProcessIdToSessionId.argtypes = [wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.ProcessIdToSessionId.restype = wt.BOOL

ntdll.NtOpenDirectoryObject.argtypes = [ctypes.POINTER(wt.HANDLE), wt.DWORD, ctypes.POINTER(OBJECT_ATTRIBUTES)]
ntdll.NtOpenDirectoryObject.restype = ctypes.c_long
ntdll.NtQueryDirectoryObject.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.ULONG, wt.BOOLEAN, wt.BOOLEAN, ctypes.POINTER(wt.ULONG), ctypes.POINTER(wt.ULONG)]
ntdll.NtQueryDirectoryObject.restype = ctypes.c_long


def out(*args):
    print(dt.datetime.now().isoformat(timespec="milliseconds"), *args, flush=True)


def snapshot():
    h = k32.CreateToolhelp32Snapshot(2, 0)
    res = {}
    if h == ctypes.c_void_p(-1).value:
        return res
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32FirstW(h, ctypes.byref(e))
    while ok:
        res[int(e.th32ProcessID)] = (int(e.th32ParentProcessID), e.szExeFile)
        ok = k32.Process32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return res


def session_ns():
    sid = wt.DWORD()
    k32.ProcessIdToSessionId(k32.GetCurrentProcessId(), ctypes.byref(sid))
    return r"\Sessions\%d\BaseNamedObjects" % sid.value


def enum_dir(path):
    b = ctypes.create_unicode_buffer(path)
    us = UNICODE_STRING(len(path) * 2, (len(path) + 1) * 2, ctypes.cast(b, ctypes.c_void_p))
    oa = OBJECT_ATTRIBUTES(ctypes.sizeof(OBJECT_ATTRIBUTES), None, ctypes.pointer(us), 0, None, None)
    h = wt.HANDLE()
    st = ntdll.NtOpenDirectoryObject(ctypes.byref(h), 1, ctypes.byref(oa))
    if st < 0:
        return []
    res = []
    buf = ctypes.create_string_buffer(65536)
    ctx = wt.ULONG(0)
    ret = wt.ULONG(0)
    first = True
    try:
        while True:
            st = ntdll.NtQueryDirectoryObject(h, buf, len(buf), True, first, ctypes.byref(ctx), ctypes.byref(ret))
            first = False
            if st == 0x8000001A or st < 0:
                break
            base = ctypes.sizeof(UNICODE_STRING)
            nu = UNICODE_STRING.from_buffer_copy(buf.raw[:base])
            tu = UNICODE_STRING.from_buffer_copy(buf.raw[base:base * 2])
            if not nu.Length:
                break
            res.append((ctypes.wstring_at(nu.Buffer, nu.Length // 2), ctypes.wstring_at(tu.Buffer, tu.Length // 2) if tu.Length else ""))
    finally:
        k32.CloseHandle(h)
    return res


def relevant(name):
    n = name.upper()
    return any(x in n for x in ("TCLS_SHAREDMEMEMORY", "TPF_SHARE_MEM", "TCLSHOST_MUTEX", "RAIL_TCLS", "TCLS_"))


def query_mapping(name):
    h = k32.OpenFileMappingW(0x0004, False, name)
    if not h:
        return None
    try:
        addr = k32.MapViewOfFile(h, 0x0002, 0, 0, 0)
        if not addr:
            return None
        mbi = MEMORY_BASIC_INFORMATION()
        if k32.VirtualQuery(ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            return mbi.RegionSize
        return None
    finally:
        if "addr" in locals() and addr:
            k32.UnmapViewOfFile(ctypes.c_void_p(addr))
        k32.CloseHandle(h)


def descendants(root_pid, procs):
    selected = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, (ppid, _) in procs.items():
            if pid not in selected and ppid in selected:
                selected.add(pid)
                changed = True
    return selected


def stop_tree(root_pid, procs):
    selected = descendants(root_pid, procs)
    rank = {}
    for pid in selected:
        r = 0
        x = pid
        while x in procs and r < 32:
            r += 1
            x = procs[x][0]
            if x == root_pid:
                break
        rank[pid] = r
    for pid in sorted(selected, key=lambda x: rank.get(x, 0), reverse=True):
        h = k32.OpenProcess(0x0001 | 0x00100000 | 0x1000, False, pid)
        if h:
            k32.TerminateProcess(h, 0)
            if pid == root_pid:
                k32.WaitForSingleObject(h, 2000)
            k32.CloseHandle(h)
    return sorted(selected)


if not os.path.isfile(TGP):
    out("MISSING", TGP)
    sys.exit(2)

base_procs = snapshot()
base_pids = set(base_procs)
base_objs = set()
for ns in (r"\BaseNamedObjects", session_ns()):
    base_objs |= {(ns, n, t) for n, t in enum_dir(ns) if relevant(n)}
out("BASELINE", "pids", len(base_pids), "objects", len(base_objs))
for ns, n, t in sorted(base_objs):
    out("BASE_OBJECT", ns, t, n)

si = STARTUPINFOW()
si.cb = ctypes.sizeof(si)
pi = PROCESS_INFORMATION()
cmd = ctypes.create_unicode_buffer(CMD)
ok = k32.CreateProcessW(TGP, cmd, None, None, False, 0, None, WEGAME, ctypes.byref(si), ctypes.byref(pi))
if not ok:
    err = ctypes.get_last_error()
    out("CREATE_FAIL", err, "fallback ShellExecuteExW runas Client.exe")
    sei = SHELLEXECUTEINFOW()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = 0x40 | 0x100
    sei.lpVerb = "runas"
    sei.lpFile = os.path.join(ROOT, "COD OL", "TCLS", "Client.exe")
    sei.lpDirectory = os.path.join(ROOT, "COD OL", "TCLS")
    sei.nShow = 1
    if not shell32.ShellExecuteExW(ctypes.byref(sei)) or not sei.hProcess:
        out("SHELLEXECUTE_FAIL", ctypes.get_last_error())
        sys.exit(4)
    pi.hProcess = sei.hProcess
    pi.dwProcessId = k32.GetProcessId(sei.hProcess)
    pi.hThread = wt.HANDLE()
    out("FALLBACK_ROOT", int(pi.dwProcessId))
root_pid = int(pi.dwProcessId)
out("CREATE", "root_pid", root_pid)
seen_objs = set()
seen_procs = set()
end = time.time() + DURATION
while time.time() < end:
    procs = snapshot()
    for pid, (ppid, name) in procs.items():
        if pid in base_pids:
            continue
        if pid in descendants(root_pid, procs) or any(x in name.lower() for x in ("tgp", "wegame", "tcls", "client")):
            if pid not in seen_procs:
                seen_procs.add(pid)
                out("PROC", pid, "ppid", ppid, name)
    for ns in (r"\BaseNamedObjects", session_ns()):
        for n, t in enum_dir(ns):
            if not relevant(n):
                continue
            key = (ns, n, t)
            if key not in base_objs and key not in seen_objs:
                seen_objs.add(key)
                size = query_mapping(n) if t.lower().startswith("section") else None
                out("OBJECT", ns, t, n, "size", size)
    time.sleep(0.2)

final = snapshot()
alive = descendants(root_pid, final)
out("STOPPING", sorted(alive))
stopped = stop_tree(root_pid, final)
out("STOPPED", stopped)
if pi.hThread:
    k32.CloseHandle(pi.hThread)
if pi.hProcess:
    k32.CloseHandle(pi.hProcess)
out("END")
