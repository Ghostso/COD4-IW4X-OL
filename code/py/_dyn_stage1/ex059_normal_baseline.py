import ctypes
import ctypes.wintypes as wt
import json
import time
from pathlib import Path

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
GAME = ROOT / "工具" / "EX035_DIR" / "codoMP_client_shipRetail.exe"
CWD = GAME.parent

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class SI(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
                ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
                ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD), ("dwXCountChars", wt.DWORD),
                ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD), ("dwFlags", wt.DWORD),
                ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD), ("lpReserved2", ctypes.c_void_p),
                ("hStdInput", wt.HANDLE), ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE), ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]


class ME(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HANDLE), ("szModule", wt.WCHAR * 256),
                ("szExePath", wt.WCHAR * 260)]


k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(SI), ctypes.POINTER(PI)]
k32.CreateProcessW.restype = wt.BOOL
k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(ME)]
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(ME)]
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.TerminateProcess.argtypes = [wt.HANDLE, wt.DWORD]
k32.CloseHandle.argtypes = [wt.HANDLE]


def modules(pid):
    handle = k32.CreateToolhelp32Snapshot(0x18, pid)
    if handle == ctypes.c_void_p(-1).value:
        return []
    result = []
    entry = ME()
    entry.dwSize = ctypes.sizeof(entry)
    ok = k32.Module32FirstW(handle, ctypes.byref(entry))
    while ok:
        result.append((entry.szModule, entry.szExePath))
        ok = k32.Module32NextW(handle, ctypes.byref(entry))
    k32.CloseHandle(handle)
    return result


def main():
    startup = SI()
    startup.cb = ctypes.sizeof(startup)
    info = PI()
    command = ctypes.create_unicode_buffer('"' + str(GAME) + '" -q')
    if not k32.CreateProcessW(str(GAME), command, None, None, False, 0, None, str(CWD), ctypes.byref(startup), ctypes.byref(info)):
        print(json.dumps({"type": "create_failed", "error": ctypes.get_last_error()}))
        return 2

    start = time.time()
    seen = set()
    periods = []
    iips = False
    while time.time() - start < 18:
        current = modules(info.dwProcessId)
        names = {Path(path).name.lower() for _, path in current}
        for name in sorted(names - seen):
            print(json.dumps({"type": "module_seen", "t": round(time.time() - start, 3), "module": name}, ensure_ascii=False), flush=True)
        seen |= names
        now_iips = "iips.dll" in names
        if now_iips != iips:
            periods.append([round(time.time() - start, 3), now_iips])
            iips = now_iips
        status = wt.DWORD()
        k32.GetExitCodeProcess(info.hProcess, ctypes.byref(status))
        if status.value != 259:
            break
        time.sleep(0.15)

    result = {"type": "summary", "pid": int(info.dwProcessId), "iips_periods": periods,
              "modules": sorted(seen), "exit_code": int(status.value)}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if status.value == 259:
        k32.TerminateProcess(info.hProcess, 0)
    k32.CloseHandle(info.hThread)
    k32.CloseHandle(info.hProcess)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
