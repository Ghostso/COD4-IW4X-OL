import ctypes
import ctypes.wintypes as wt
import sys
import time
from pathlib import Path

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

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
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]

user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
user32.EnumWindows.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]


def windows_for(pid):
    found = []

    def enum_proc(hwnd, lp):
        wpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid:
            b = ctypes.create_unicode_buffer(4096)
            user32.GetWindowTextW(hwnd, b, len(b))
            found.append(b.value)
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)(enum_proc), 0)
    return found


def main():
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmd = ctypes.create_unicode_buffer('"' + str(GAME_EXP) + '" -q')
    k32.CreateProcessW(str(GAME_EXP), cmd, None, None, False, 0, None, str(EXP), ctypes.byref(si), ctypes.byref(pi))
    pid = int(pi.dwProcessId)
    end = time.time() + 20
    while time.time() < end:
        if any("致命错误" in t for t in windows_for(pid)):
            break
        time.sleep(0.2)
    h = k32.OpenProcess(0x0010 | 0x0400, False, pid)
    if not h:
        return 5
    start = 0x755860
    size = 0x260
    buf = ctypes.create_string_buffer(size)
    rd = ctypes.c_size_t()
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(start), buf, size, ctypes.byref(rd))
    print("READ", ok, rd.value)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for ins in md.disasm(buf.raw[:rd.value], start):
        print(hex(ins.address), ins.mnemonic, ins.op_str)
    k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(h)
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)
    return 0


if __name__ == "__main__":
    sys.exit(main())
