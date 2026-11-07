import ctypes
import ctypes.wintypes as wt
import datetime as dt
import os
import sys
import time

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
GAME = os.path.join(ROOT, "COD OL", "codoMP_client_shipRetail.exe")
GAMEDIR = os.path.join(ROOT, "COD OL")
DURATION = 20

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD), ("szExeFile", wt.WCHAR * 260),
    ]


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ThreadID", wt.DWORD),
        ("th32OwnerProcessID", wt.DWORD), ("tpBasePri", wt.LONG), ("tpDeltaPri", wt.LONG),
        ("dwFlags", wt.DWORD),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wt.DWORD), ("hModule", wt.HANDLE), ("szModule", wt.WCHAR * 256),
        ("szExePath", wt.WCHAR * 260),
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


k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Thread32First.argtypes = [wt.HANDLE, ctypes.POINTER(THREADENTRY32)]
k32.Thread32Next.argtypes = [wt.HANDLE, ctypes.POINTER(THREADENTRY32)]
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.OpenThread.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenThread.restype = wt.HANDLE
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.GetExitCodeProcess.restype = wt.BOOL
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
k32.CreateProcessW.restype = wt.BOOL
k32.GetCurrentProcessId.argtypes = []
k32.GetCurrentProcessId.restype = wt.DWORD
k32.ProcessIdToSessionId.argtypes = [wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.ProcessIdToSessionId.restype = wt.BOOL

ntdll.NtOpenDirectoryObject.argtypes = [ctypes.POINTER(wt.HANDLE), wt.DWORD, ctypes.POINTER(OBJECT_ATTRIBUTES)]
ntdll.NtOpenDirectoryObject.restype = ctypes.c_long
ntdll.NtQueryDirectoryObject.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.ULONG, wt.BOOLEAN, wt.BOOLEAN, ctypes.POINTER(wt.ULONG), ctypes.POINTER(wt.ULONG)]
ntdll.NtQueryDirectoryObject.restype = ctypes.c_long
ntdll.NtQueryInformationThread.argtypes = [wt.HANDLE, wt.ULONG, ctypes.c_void_p, wt.ULONG, ctypes.POINTER(wt.ULONG)]
ntdll.NtQueryInformationThread.restype = ctypes.c_long


def out(*args):
    print(dt.datetime.now().isoformat(timespec="milliseconds"), *args, flush=True)


def procs():
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


def threads(pid):
    h = k32.CreateToolhelp32Snapshot(4, 0)
    res = []
    if h == ctypes.c_void_p(-1).value:
        return res
    e = THREADENTRY32()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Thread32First(h, ctypes.byref(e))
    while ok:
        if int(e.th32OwnerProcessID) == pid:
            res.append(int(e.th32ThreadID))
        ok = k32.Thread32Next(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return res


def thread_start(tid):
    h = k32.OpenThread(0x40, False, tid)
    if not h:
        return None
    try:
        start = ctypes.c_void_p()
        ret = wt.ULONG()
        st = ntdll.NtQueryInformationThread(h, 9, ctypes.byref(start), ctypes.sizeof(start), ctypes.byref(ret))
        if st < 0:
            return None
        return int(start.value or 0)
    finally:
        k32.CloseHandle(h)


def modules(pid):
    h = k32.CreateToolhelp32Snapshot(0x18, pid)
    res = []
    if h == ctypes.c_void_p(-1).value:
        return res
    e = MODULEENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Module32FirstW(h, ctypes.byref(e))
    while ok:
        res.append((e.szExePath, int(e.modBaseAddr or 0), int(e.modBaseSize)))
        ok = k32.Module32NextW(h, ctypes.byref(e))
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
    if ntdll.NtOpenDirectoryObject(ctypes.byref(h), 1, ctypes.byref(oa)) < 0:
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
    return any(x in n for x in ("TCLS_SHAREDMEMEMORY", "TPF_SHARE_MEM", "TCLSHOST_MUTEX", "FSYNCSHAREDMEMORY", "RAIL_TCLS"))


def named_all():
    outv = set()
    for ns in (r"\BaseNamedObjects", session_ns()):
        outv |= {(ns, n, t) for n, t in enum_dir(ns) if relevant(n)}
    return outv


def snapshot_files():
    roots = [os.path.join(GAMEDIR, "players"), os.path.join(GAMEDIR, "main"), os.path.join(GAMEDIR, "Logs"),
             os.path.join(GAMEDIR, "TenproxyLog"), os.path.join(GAMEDIR, "BugTrace.log"), os.path.join(GAMEDIR, "debug.log")]
    res = {}
    for r in roots:
        if os.path.isfile(r):
            try:
                st = os.stat(r)
                res[r] = (st.st_size, st.st_mtime_ns)
            except OSError:
                pass
        elif os.path.isdir(r):
            for base, _, files in os.walk(r):
                for f in files:
                    p = os.path.join(base, f)
                    try:
                        st = os.stat(p)
                        res[p] = (st.st_size, st.st_mtime_ns)
                    except OSError:
                        pass
    return res


if not os.path.isfile(GAME):
    out("MISSING", GAME)
    sys.exit(2)

base_procs = procs()
base_pids = set(base_procs)
base_objs = named_all()
base_files = snapshot_files()
out("BASELINE_PROCESSES", len(base_pids))
for pid, (ppid, name) in sorted(base_procs.items()):
    if any(x in name.lower() for x in ("wegame", "tgp", "tcls", "launcher", "client", "tenio", "tencent")):
        out("BASELINE_TENCENT_PROCESS", pid, ppid, name)
for obj in sorted(base_objs):
    out("BASELINE_OBJECT", *obj)
out("BASELINE_FILES", len(base_files))

si = STARTUPINFOW()
si.cb = ctypes.sizeof(si)
pi = PROCESS_INFORMATION()
cmd = ctypes.create_unicode_buffer('"' + GAME + '"')
started = k32.CreateProcessW(GAME, cmd, None, None, False, 0, None, GAMEDIR, ctypes.byref(si), ctypes.byref(pi))
if not started:
    out("CREATE_FAIL", ctypes.get_last_error())
    sys.exit(4)
pid = int(pi.dwProcessId)
out("CREATE", "PID", pid, "PARENT", os.getpid(), "CMD", cmd.value, "CWD", GAMEDIR)

seen_mods = set()
seen_tids = set()
seen_objs = set(base_objs)
exit_code = None
end = time.time() + DURATION
while time.time() < end:
    now = time.time()
    for path, base, size in modules(pid):
        if path not in seen_mods:
            seen_mods.add(path)
            out("MODULE_LOAD", "t=%.3f" % (now - (end - DURATION)), path, "base", hex(base), "size", hex(size))
    for tid in threads(pid):
        if tid not in seen_tids:
            seen_tids.add(tid)
            out("THREAD", "t=%.3f" % (now - (end - DURATION)), "TID", tid, "start", hex(thread_start(tid) or 0))
    for obj in named_all():
        if obj not in seen_objs:
            seen_objs.add(obj)
            out("OBJECT", "t=%.3f" % (now - (end - DURATION)), *obj)
    code = wt.DWORD()
    if k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code)) and code.value != 259:
        exit_code = int(code.value)
        out("EXIT", exit_code)
        break
    time.sleep(0.2)

final_code = wt.DWORD()
k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(final_code))
alive = final_code.value == 259
out("FINAL_EXIT", None if alive else int(final_code.value))
if alive:
    out("TERMINATE", pid)
    k32.TerminateProcess(pi.hProcess, 0)

post_files = snapshot_files()
for p, m in post_files.items():
    if p not in base_files or base_files[p] != m:
        out("FILE_CHANGED", p, m)
for obj in sorted(named_all() - base_objs):
    out("FINAL_NEW_OBJECT", *obj)
k32.CloseHandle(pi.hThread)
k32.CloseHandle(pi.hProcess)
out("END")
