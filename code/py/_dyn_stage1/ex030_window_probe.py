import ctypes
import ctypes.wintypes as wt
import os
import sys
import time

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
GAME = os.path.join(ROOT, "COD OL", "codoMP_client_shipRetail.exe")
GAMEDIR = os.path.join(ROOT, "COD OL")

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
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]

user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
user32.EnumWindows.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.EnumChildWindows.argtypes = [wt.HWND, ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]


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


def window_text(hwnd):
    b = ctypes.create_unicode_buffer(4096)
    user32.GetWindowTextW(hwnd, b, len(b))
    return b.value


def class_name(hwnd):
    b = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, b, len(b))
    return b.value


found_windows = []


def enum_proc(hwnd, lparam):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == target_pid[0]:
        found_windows.append((hwnd, class_name(hwnd), window_text(hwnd)))
    return True


def enum_child_proc(hwnd, lparam):
    found_windows.append((hwnd, class_name(hwnd), window_text(hwnd)))
    return True


if not os.path.isfile(GAME):
    print("MISSING", GAME)
    sys.exit(2)

si = STARTUPINFOW()
si.cb = ctypes.sizeof(si)
pi = PROCESS_INFORMATION()
cmd = ctypes.create_unicode_buffer('"' + GAME + '"')
if not k32.CreateProcessW(GAME, cmd, None, None, False, 0, None, GAMEDIR, ctypes.byref(si), ctypes.byref(pi)):
    print("CREATE_FAIL", ctypes.get_last_error())
    sys.exit(4)
pid = int(pi.dwProcessId)
target_pid = [pid]
print("PID", pid, "PARENT", os.getpid())

end = time.time() + 20
while time.time() < end:
    found_windows.clear()
    user32.EnumWindows(ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)(enum_proc), 0)
    if found_windows:
        break
    time.sleep(0.25)

print("WINDOWS", len(found_windows))
for hwnd, cls, text in found_windows:
    print("WIN", hex(hwnd), cls, repr(text))
    children = []

    def child_proc(ch, lp):
        children.append((ch, class_name(ch), window_text(ch)))
        return True

    user32.EnumChildWindows(hwnd, ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)(child_proc), 0)
    for ch, ccls, ctext in children:
        print(" CHILD", hex(ch), ccls, repr(ctext))

mods = modules(pid)
print("MODULES", len(mods))
for path, base, size in mods:
    low = path.lower()
    if any(x in low for x in ("tenproxy", "gbspy", "tenrpcs", "gamerpcs", "tcj.dll", "gdploader",
                              "gamedataplatformserver", "policyprobe", "ace-drv32", "tersafe",
                              "libcef", "base.dll", "bugtrace")):
        print("MOD", path, hex(base), hex(size))

if pi.hThread:
    k32.CloseHandle(pi.hThread)
if pi.hProcess:
    k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(pi.hProcess)
print("END")
