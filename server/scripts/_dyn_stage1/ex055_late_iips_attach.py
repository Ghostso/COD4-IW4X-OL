import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
GAME = Path(r"X:\codoMP_client_shipRetail.exe")
CDB = ROOT / "工具" / "windbg_x86" / "cdb.exe"
ATTACH_LOG = Path(r"X:\ex055_attach_controller.log")

TH32CS_SNAPPROCESS = 0x2
TH32CS_SNAPMODULE = 0x8
TH32CS_SNAPMODULE32 = 0x10
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
        ("szExeFile", wt.WCHAR * 260),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD),
        ("modBaseAddr", ctypes.c_void_p), ("modBaseSize", wt.DWORD),
        ("hModule", wt.HANDLE), ("szModule", wt.WCHAR * 256),
        ("szExePath", wt.WCHAR * 260),
    ]


k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32FirstW.restype = wt.BOOL
k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.restype = wt.BOOL
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32FirstW.restype = wt.BOOL
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32NextW.restype = wt.BOOL
k32.CloseHandle.argtypes = [wt.HANDLE]


def snapshot_modules(pid):
    handle = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if handle == INVALID_HANDLE_VALUE:
        return []
    result = []
    entry = MODULEENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    ok = k32.Module32FirstW(handle, ctypes.byref(entry))
    while ok:
        result.append((entry.szModule, entry.szExePath, int(entry.modBaseAddr or 0)))
        ok = k32.Module32NextW(handle, ctypes.byref(entry))
    k32.CloseHandle(handle)
    return result


def snapshot_processes():
    handle = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if handle == INVALID_HANDLE_VALUE:
        return {}
    result = {}
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    ok = k32.Process32FirstW(handle, ctypes.byref(entry))
    while ok:
        result[int(entry.th32ProcessID)] = (entry.szExeFile, int(entry.th32ParentProcessID))
        ok = k32.Process32NextW(handle, ctypes.byref(entry))
    k32.CloseHandle(handle)
    return result


def log_line(stream, text):
    line = f"{time.strftime('%H:%M:%S')} {text}"
    print(line, flush=True)
    stream.write(line + "\n")
    stream.flush()


def make_cdb_command(iips_base):
    def addr(offset):
        return f"0x{iips_base + offset:08x}"

    commands = [
        ".logopen /t X:\\ex055_iips_breakpoints.log",
        "sxd av",
        "sxd eh",
        "sxd bpe",
        f"bp {addr(0x9860)} ".replace(" ", " ", 1) + '".echo IIPS_InitInGameApp; r; k; g"',
        f"bp {addr(0x9570)} ".replace(" ", " ", 1) + '".echo IIPS_initIfsLib; r; k; g"',
        f"bp {addr(0x96e9)} ".replace(" ", " ", 1) + '".echo LoadLibraryW_BEFORE; r; dd @esp L4; du poi(@esp+4); du @esp+4; k; g"',
        f"bp {addr(0x96ef)} ".replace(" ", " ", 1) + '"echo LoadLibraryW_AFTER; r eax; !gle; dd fs:[34] L1; k; g"'.replace('"echo', '".echo') ,
        f"bp {addr(0x977c)} ".replace(" ", " ", 1) + '"echo GetProcAddress_Create_BEFORE; r; dd @esp L3; da poi(@esp+4); k; g"'.replace('"echo', '".echo'),
        f"bp {addr(0x977e)} ".replace(" ", " ", 1) + '"echo GetProcAddress_Create_AFTER; r eax; k; g"'.replace('"echo', '".echo'),
        f"bp {addr(0x97a5)} ".replace(" ", " ", 1) + '"echo CreateIFSLibDll_BEFORE; r eax; dd @esp L4; k; g"'.replace('"echo', '".echo'),
        f"bp {addr(0x97a7)} ".replace(" ", " ", 1) + '"echo CreateIFSLibDll_AFTER; r eax; k; g"'.replace('"echo', '".echo'),
        f"bp {addr(0x97cc)} ".replace(" ", " ", 1) + '"echo GetProcAddress_Destroy_BEFORE; r; dd @esp L3; da poi(@esp+4); k; g"'.replace('"echo', '".echo'),
        f"bp {addr(0x97d3)} ".replace(" ", " ", 1) + '"echo GetProcAddress_Destroy_AFTER; r eax; k; g"'.replace('"echo', '".echo'),
        f"bp {addr(0x9a8b)} ".replace(" ", " ", 1) + '"echo GetPrivateProfileIntW; r; du poi(@esp+4); du poi(@esp+8); du poi(@esp+10); dd @esp L5; k; g"'.replace('"echo', '".echo'),
        f"bp {addr(0x9a91)} ".replace(" ", " ", 1) + '"echo GetPrivateProfileIntW_AFTER; r eax; k; g"'.replace('"echo', '".echo'),
        f"bp {addr(0x1194e)} ".replace(" ", " ", 1) + '"echo OpenFileMappingA; r; da poi(@esp+0c); dd @esp L4; k; g"'.replace('"echo', '".echo'),
        f"bp {addr(0x1197b)} ".replace(" ", " ", 1) + '"echo CreateMutexA; r; da poi(@esp+0c); dd @esp L4; k; g"'.replace('"echo', '".echo'),
        f"bp {addr(0x15cd1)} ".replace(" ", " ", 1) + '"echo ShellExecuteExW_BEFORE; r; dd @esp L2; dd poi(@esp+4) L10; du poi(poi(@esp+4)+10); du poi(poi(@esp+4)+0c); k; g"'.replace('"echo', '".echo'),
        f"bp {addr(0x15cd7)} ".replace(" ", " ", 1) + '"echo ShellExecuteExW_AFTER; r eax; dd poi(@esp+4)+20 L1; k; g"'.replace('"echo', '".echo'),
        "g",
        ".logclose",
        "q",
    ]
    return ";".join(commands)


def main():
    if not CDB.exists():
        print("CDB_MISSING", CDB)
        return 2
    with ATTACH_LOG.open("w", encoding="utf-8") as controller:
        process = subprocess.Popen([str(GAME), "-q"], cwd="X:\\")
        log_line(controller, f"GAME_PID={process.pid}")
        start = time.time()
        seen = set()
        iips_base = None
        while time.time() - start < 12 and process.poll() is None:
            mods = snapshot_modules(process.pid)
            names = {name.lower() for name, _, _ in mods}
            for name, path, base in mods:
                key = name.lower()
                if key not in seen:
                    seen.add(key)
                    log_line(controller, f"MODULE {name} BASE=0x{base:08x} PATH={path}")
                if key == "iips.dll":
                    iips_base = base
            if iips_base:
                log_line(controller, f"IIPS_SEEN BASE=0x{iips_base:08x}")
                command = make_cdb_command(iips_base)
                log_line(controller, "ATTACH_CDB_START")
                result = subprocess.run([
                    str(CDB), "-o", "-p", str(process.pid), "-c", command
                ], cwd="X:\\", capture_output=True, text=True, errors="replace", timeout=10)
                Path(r"X:\ex055_cdb_stdout.log").write_text(result.stdout + "\nSTDERR\n" + result.stderr, encoding="utf-8")
                log_line(controller, f"ATTACH_CDB_EXIT={result.returncode}")
                break
            time.sleep(0.02)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(2)
            except subprocess.TimeoutExpired:
                process.kill()
        log_line(controller, f"GAME_EXIT={process.returncode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
