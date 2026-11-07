import ctypes
import ctypes.wintypes as wt
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
SRC = Path(ROOT) / "COD OL"
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
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
k32.CreateProcessW.restype = wt.BOOL
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]

user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
user32.EnumWindows.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]


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


def module_for(addr, mods):
    for path, base, size in mods:
        if base <= addr < base + size:
            return path, addr - base
    return None, None


def find_all(hay, needle):
    out = []
    pos = 0
    while True:
        pos = hay.find(needle, pos)
        if pos < 0:
            return out
        out.append(pos)
        pos += 1


def readable(prot):
    return bool(prot & 0xFE) and not (prot & (0x100 | 0x80 | 0x1000000))


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


def main(args):
    label = args[0]
    tokens = args[1:]
    if not EXP.is_dir():
        raise SystemExit("MISSING_EXP_DIR")
    if not GAME_EXP.is_file():
        raise SystemExit("MISSING_EXP_GAME")

    cmd_parts = ['"' + str(GAME_EXP) + '"'] + tokens
    cmd = ctypes.create_unicode_buffer(" ".join(cmd_parts))

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    ok = k32.CreateProcessW(str(GAME_EXP), cmd, None, None, False, 0, None, str(EXP), ctypes.byref(si), ctypes.byref(pi))
    pid = int(pi.dwProcessId)
    print("PROBE", label, "PID", pid, "CMD", " ".join(cmd_parts), "CREATE", bool(ok), "ERR", ctypes.get_last_error() if not ok else 0)
    if not ok:
        return 1

    start = time.time()
    all_windows = []
    all_mods = []
    global_bytes = {}
    died = False
    exit_code = None

    while time.time() - start < 18:
        wins = windows_for(pid)
        if wins:
            all_windows = wins
        mods = modules(pid)
        if mods:
            all_mods = mods
        st = wt.DWORD()
        k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(st))
        if st.value != 259:
            died = True
            exit_code = hex(st.value)
            break

        h = k32.OpenProcess(0x0010 | 0x0400, False, pid)
        if h:
            mbi = MEMORY_BASIC_INFORMATION()
            addr = 0x00400000
            while addr < 0x7FFF0000:
                if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                    break
                if mbi.State == 0x1000 and readable(mbi.Protect) and mbi.RegionSize:
                    base = int(mbi.BaseAddress or 0)
                    if base <= 0x849B501 < base + mbi.RegionSize and 0x849413B not in global_bytes:
                        buf = ctypes.create_string_buffer(mbi.RegionSize)
                        rd = ctypes.c_size_t()
                        if k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, mbi.RegionSize, ctypes.byref(rd)):
                            data = buf.raw[:rd.value]
                            if 0x849413B >= base and 0x849413B < base + len(data):
                                global_bytes["0x849413B"] = data[0x849413B - base]
                                global_bytes["0x849B500"] = data[0x849B500 - base]
                                global_bytes["0x849B501"] = data[0x849B501 - base]
                addr += max(mbi.RegionSize, 1)
            k32.CloseHandle(h)
        time.sleep(0.3)

    if not died:
        k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)

    interest = ("tenproxy", "gbspy", "tenrpcs", "gamerpcs", "tcj.dll", "gdploader",
                "gamedataplatformserver", "policyprobe", "ace-drv32", "tersafe",
                "libcef", "base.dll", "bugtrace", "vsddrv", "audi",
                "iips", "ifs", "hostapp", "download")
    loaded = sorted(set(Path(p).name for p, _, _ in all_mods if any(x in p.lower() for x in interest)))
    print("RESULT", label)
    print("DIED", died, "EXIT", exit_code)
    print("WINDOWS", len(all_windows))
    for hwnd, cls, text in all_windows:
        print("WIN", hwnd, cls, repr(text))
    print("MODULES", len(all_mods))
    print("LOADED", loaded)
    print("GLOBALS", global_bytes)
    print("DURATION", round(time.time() - start, 3))
    print("END")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
