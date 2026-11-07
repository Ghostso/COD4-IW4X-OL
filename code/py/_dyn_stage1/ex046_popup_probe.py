import ctypes
import ctypes.wintypes as wt
import sys
import time
from pathlib import Path

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
EXP = Path(ROOT) / "工具" / "EX035_DIR"
GAME_EXP = EXP / "codoMP_client_shipRetail.exe"

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)


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


k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
k32.CreateProcessW.restype = wt.BOOL
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]

user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
user32.EnumWindows.restype = wt.BOOL
user32.EnumChildWindows.argtypes = [wt.HWND, ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]


def text_of(hwnd):
    b = ctypes.create_unicode_buffer(4096)
    user32.GetWindowTextW(hwnd, b, len(b))
    return b.value


def cls_of(hwnd):
    b = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, b, len(b))
    return b.value


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "B"
    args = [] if mode == "A" else (["-q"] if mode == "B" else ["-qa"])
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmd = ctypes.create_unicode_buffer(" ".join(['"' + str(GAME_EXP) + '"'] + args))
    ok = k32.CreateProcessW(str(GAME_EXP), cmd, None, None, False, 0, None, str(EXP), ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print("CREATE_FAIL", ctypes.get_last_error())
        return 4
    pid = int(pi.dwProcessId)
    print("MODE", mode, "PID", pid)
    start = time.time()
    found = None
    while time.time() - start < 20:
        wins = []

        def enum(hwnd, lp):
            wpid = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
            if wpid.value == pid:
                wins.append(hwnd)
            return True

        user32.EnumWindows(ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)(enum), 0)
        for hwnd in wins:
            if cls_of(hwnd) == "#32770":
                found = (hwnd, round(time.time() - start, 3))
                break
        if found:
            break
        time.sleep(0.2)
    if not found:
        print("NO_DIALOG")
    else:
        hwnd, t = found
        print("DIALOG_T", t, "HWND", hex(int(hwnd)), "CLASS", cls_of(hwnd), "TITLE", repr(text_of(hwnd)))
        kids = []

        def enum_kids(h, lp):
            kids.append(h)
            return True

        user32.EnumChildWindows(hwnd, ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)(enum_kids), 0)
        for h in kids:
            print("CHILD", hex(int(h)), cls_of(h), repr(text_of(h)))
    k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)
    return 0


if __name__ == "__main__":
    sys.exit(main())
