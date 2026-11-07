import ctypes
import ctypes.wintypes as wt
import os
import sys
import time
from pathlib import Path

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
EXP = Path(ROOT) / "工具" / "EX035_DIR"
GAME_EXP = EXP / "codoMP_client_shipRetail.exe"

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD), ("szExeFile", wt.WCHAR * 260),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wt.DWORD), ("hModule", wt.HANDLE), ("szModule", wt.WCHAR * 256),
        ("szExePath", wt.WCHAR * 260),
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
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
k32.CreateProcessW.restype = wt.BOOL
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]

user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
user32.EnumWindows.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]


def modules(pid):
    h = k32.CreateToolhelp32Snapshot(0x18, pid)
    if h == ctypes.c_void_p(-1).value:
        return []
    outv = []
    e = MODULEENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Module32FirstW(h, ctypes.byref(e))
    while ok:
        outv.append((e.szExePath, int(e.modBaseAddr or 0), int(e.modBaseSize)))
        ok = k32.Module32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return outv


def procs():
    h = k32.CreateToolhelp32Snapshot(2, 0)
    out = {}
    if h == ctypes.c_void_p(-1).value:
        return out
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32FirstW(h, ctypes.byref(e))
    while ok:
        out[int(e.th32ProcessID)] = (int(e.th32ParentProcessID), e.szExeFile)
        ok = k32.Process32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return out


def windows_for(pid):
    found = []

    def enum_proc(hwnd, lp):
        wpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid:
            b = ctypes.create_unicode_buffer(4096)
            user32.GetWindowTextW(hwnd, b, len(b))
            c = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, c, len(c))
            found.append((hex(int(hwnd)), c.value, b.value))
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)(enum_proc), 0)
    return found


def main():
    if not EXP.is_dir() or not GAME_EXP.is_file():
        print("MISSING_EXP")
        return 1
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmd = ctypes.create_unicode_buffer('"' + str(GAME_EXP) + '"')
    ok = k32.CreateProcessW(str(GAME_EXP), cmd, None, None, False, 0, None, str(EXP), ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print("CREATE_FAIL", ctypes.get_last_error())
        return 4
    pid = int(pi.dwProcessId)
    parent = procs().get(pid, (0, ""))
    print("PID", pid, "PARENT", parent[0], "IMAGE", parent[1])

    start = time.time()
    all_windows = []
    all_mods = []
    iips_periods = []
    prev_iips = False

    while time.time() - start < 18:
        wins = windows_for(pid)
        if wins:
            all_windows = wins
        mods = modules(pid)
        if mods:
            all_mods = mods
        names = [Path(p).name.lower() for p, _, _ in mods]
        has_iips = any(n == "iips.dll" for n in names)
        if has_iips != prev_iips:
            iips_periods.append((round(time.time() - start, 3), has_iips))
            prev_iips = has_iips
        st = wt.DWORD()
        k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(st))
        if st.value != 259:
            print("EXITED", hex(st.value))
            break
        time.sleep(0.2)

    print("WINDOWS")
    for hwnd, cls, text in all_windows:
        print("WIN", hwnd, cls, repr(text))
    print("MODULES")
    for p, base, size in sorted(all_mods, key=lambda x: x[1]):
        low = p.lower()
        if any(x in low for x in ("iips", "ifs", "hostapp", "tenproxy", "gbspy", "tenrpcs",
                                  "gamerpcs", "tcj.dll", "gdploader", "policyprobe", "libcef",
                                  "base.dll", "bugtrace")):
            print("MOD", p, hex(base), hex(size))
    print("IIPS_PERIODS", iips_periods)
    print("TOTAL_MODULES", len(all_mods))

    k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)
    return 0


if __name__ == "__main__":
    sys.exit(main())
