import ctypes
import ctypes.wintypes as wt
import time
from pathlib import Path

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
EXP = Path(ROOT) / "工具" / "EX035_DIR"
GAME_EXP = EXP / "codoMP_client_shipRetail.exe"

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32")


class SI(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD), ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD), ("dwFlags", wt.DWORD),
        ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD), ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wt.HANDLE), ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE),
    ]


class PI(ctypes.Structure):
    _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE), ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]


class ME(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wt.DWORD), ("hModule", wt.HANDLE), ("szModule", wt.WCHAR * 256),
        ("szExePath", wt.WCHAR * 260),
    ]


k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(SI), ctypes.POINTER(PI)]
k32.CreateProcessW.restype = wt.BOOL
k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(ME)]
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(ME)]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]

user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]


def main():
    si = SI()
    si.cb = ctypes.sizeof(si)
    pi = PI()
    cmdtext = '"' + str(GAME_EXP) + '" -q'
    cmd = ctypes.create_unicode_buffer(cmdtext)
    ok = k32.CreateProcessW(str(GAME_EXP), cmd, None, None, False, 0, None, str(EXP), ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print("CREATE_FAIL", ctypes.get_last_error())
        return 4
    pid = int(pi.dwProcessId)
    print("PID", pid)

    dialog = False
    end = time.time() + 15

    def enum(hwnd, lp):
        nonlocal dialog
        wpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid:
            b = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, b, 256)
            if "致命错误" in b.value:
                dialog = True
        return True

    while time.time() < end:
        user32.EnumWindows(ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)(enum), 0)
        if dialog:
            break
        time.sleep(0.2)
    print("DIALOG", dialog)

    h = k32.CreateToolhelp32Snapshot(0x18, pid)
    names = []
    if h != ctypes.c_void_p(-1).value:
        e = ME()
        e.dwSize = ctypes.sizeof(e)
        okk = k32.Module32FirstW(h, ctypes.byref(e))
        c = 0
        while okk and c < 1500:
            low = e.szExePath.lower()
            if any(x in low for x in ("iips", "ifs", "tenproxy", "gbspy", "tenrpcs", "gamerpcs", "tcj.dll", "policyprobe")):
                names.append((e.szExePath, hex(int(e.modBaseAddr or 0)), e.modBaseSize))
            okk = k32.Module32NextW(h, ctypes.byref(e))
            c += 1
        k32.CloseHandle(h)
    print("MODS", names)
    try:
        k32.TerminateProcess(pi.hProcess, 0)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
