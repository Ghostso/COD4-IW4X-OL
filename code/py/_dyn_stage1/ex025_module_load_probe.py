import ctypes
import ctypes.wintypes as wt
import datetime as dt
import os
import sys
import time

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
CLIENT = os.path.join(ROOT, "COD OL", "TCLS", "Client.exe")

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)


class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD), ("fMask", wt.ULONG), ("hwnd", wt.HWND),
        ("lpVerb", wt.LPCWSTR), ("lpFile", wt.LPCWSTR), ("lpParameters", wt.LPCWSTR),
        ("lpDirectory", wt.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wt.HANDLE),
        ("lpIDList", ctypes.c_void_p), ("lpClass", wt.LPCWSTR), ("hkeyClass", wt.HANDLE),
        ("dwHotKey", wt.DWORD), ("hIcon", wt.HANDLE), ("hProcess", wt.HANDLE),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD), ("szExeFile", wt.WCHAR * 260),
    ]


k32.ShellExecuteExW = None
shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
shell32.ShellExecuteExW.restype = wt.BOOL
k32.GetProcessId.argtypes = [wt.HANDLE]
k32.GetProcessId.restype = wt.DWORD
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
psapi.EnumProcessModulesEx.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), wt.DWORD]
psapi.EnumProcessModulesEx.restype = wt.BOOL
psapi.GetModuleFileNameExW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.LPWSTR, wt.DWORD]
psapi.GetModuleFileNameExW.restype = wt.DWORD


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


def descendants(root, p):
    sel = {root}
    ch = True
    while ch:
        ch = False
        for pid, (ppid, _) in p.items():
            if pid not in sel and ppid in sel:
                sel.add(pid)
                ch = True
    return sel


def modules(pid):
    h = k32.OpenProcess(0x0410, False, pid)
    if not h:
        return []
    try:
        need = wt.DWORD()
        buf = (ctypes.c_void_p * 1024)()
        if not psapi.EnumProcessModulesEx(h, ctypes.cast(buf, ctypes.c_void_p), ctypes.sizeof(buf), ctypes.byref(need), 3):
            return []
        outv = []
        for i in range(min(need.value // ctypes.sizeof(ctypes.c_void_p), len(buf))):
            name = ctypes.create_unicode_buffer(2048)
            if psapi.GetModuleFileNameExW(h, buf[i], name, len(name)):
                outv.append(name.value)
        return outv
    finally:
        k32.CloseHandle(h)


if not os.path.isfile(CLIENT):
    out("MISSING", CLIENT)
    sys.exit(2)

base = procs()
sei = SHELLEXECUTEINFOW()
sei.cbSize = ctypes.sizeof(sei)
sei.fMask = 0x40 | 0x100
sei.lpVerb = "runas"
sei.lpFile = CLIENT
sei.lpDirectory = os.path.dirname(CLIENT)
sei.nShow = 1
if not shell32.ShellExecuteExW(ctypes.byref(sei)) or not sei.hProcess:
    out("SHELLEXECUTE_FAIL", ctypes.get_last_error())
    sys.exit(3)
root = int(k32.GetProcessId(sei.hProcess))
out("ROOT", root)
time.sleep(9)
allp = procs()
sel = descendants(root, allp)
out("TREE", sorted(sel))
for pid in sorted(sel):
    name = allp.get(pid, ("", ""))[1]
    mods = modules(pid)
    hits = [m for m in mods if any(x.lower() in m.lower() for x in ("tcls", "client", "launcher", "tgp", "wegame"))]
    out("MODS", pid, name)
    for m in hits:
        out(" ", m)
# Cleanup
rank = {}
for pid in sel:
    r = 0
    x = pid
    while x in allp and r < 32:
        r += 1
        x = allp[x][0]
        if x == root:
            break
    rank[pid] = r
for pid in sorted(sel, key=lambda x: rank.get(x, 0), reverse=True):
    h = k32.OpenProcess(0x1001, False, pid)
    if h:
        k32.TerminateProcess(h, 0)
        if pid == root:
            k32.WaitForSingleObject(h, 2000)
        k32.CloseHandle(h)
if sei.hProcess:
    k32.CloseHandle(sei.hProcess)
out("END")
