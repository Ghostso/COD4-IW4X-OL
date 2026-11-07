import ctypes, ctypes.wintypes as wt
import os, sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD), ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD), ("dwFlags", wt.DWORD),
        ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD), ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wt.HANDLE), ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE)
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wt.HANDLE), ("hThread", wt.HANDLE),
        ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)
    ]

k32.CreateProcessW.restype = wt.BOOL
k32.CreateProcessW.argtypes = [
    wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
    wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR,
    ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)
]
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualAllocEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
k32.WriteProcessMemory.restype = wt.BOOL
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.CreateRemoteThread.restype = wt.HANDLE
k32.CreateRemoteThread.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.ResumeThread.restype = wt.DWORD
k32.ResumeThread.argtypes = [wt.HANDLE]
k32.WaitForSingleObject.restype = wt.DWORD
k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
k32.CloseHandle.restype = wt.BOOL
k32.CloseHandle.argtypes = [wt.HANDLE]

def launch_and_inject(exe_path, dll_path, args="-qa", cwd=None):
    if cwd is None:
        cwd = os.path.dirname(exe_path)
    
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    pi = PROCESS_INFORMATION()
    
    cmdline = f'"{exe_path}" {args}'
    CREATE_SUSPENDED = 0x00000004
    
    print(f"Creating suspended process: {cmdline}")
    ok = k32.CreateProcessW(None, cmdline, None, None, False, CREATE_SUSPENDED, None, cwd, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print(f"CreateProcessW failed: {ctypes.get_last_error()}")
        return None
    
    pid = pi.dwProcessId
    hProc = pi.hProcess
    hThread = pi.hThread
    print(f"Process created suspended, PID={pid}")
    
    # Inject dll_path
    raw_dll = dll_path.encode("utf-16le") + b"\x00\x00"
    pRemote = k32.VirtualAllocEx(hProc, None, len(raw_dll) + 16, 0x3000, 0x04) # PAGE_READWRITE
    n = ctypes.c_size_t(0)
    k32.WriteProcessMemory(hProc, ctypes.c_void_p(pRemote), raw_dll, len(raw_dll), ctypes.byref(n))
    print(f"Allocated remote DLL path @ 0x{pRemote:X}")
    
    # In 32-bit SysWOW64, LoadLibraryW is at known RVA 0x21960 or resolve
    # But wait: from 64-bit to 32-bit process, CreateRemoteThread needs 32-bit start
    # Let's see if CreateRemoteThread succeeds at t=0 before anti-cheat loads!
    # At t=0 (CREATE_SUSPENDED), anti-cheat is NOT loaded yet!
    # So CreateRemoteThread is completely unrestricted!
    
    k32_mod = k32.GetModuleHandleW("kernel32.dll")
    pLoadLib = k32.GetProcAddress(k32_mod, b"LoadLibraryW")
    
    tid = wt.DWORD(0)
    th = k32.CreateRemoteThread(hProc, None, 0, ctypes.c_void_p(pLoadLib), ctypes.c_void_p(pRemote), 0, ctypes.byref(tid))
    if th:
        print(f"CreateRemoteThread SUCCESS (tid={tid.value})")
        k32.WaitForSingleObject(th, 3000)
        k32.CloseHandle(th)
    else:
        print(f"CreateRemoteThread failed: {ctypes.get_last_error()}")
    
    print("Resuming main thread...")
    k32.ResumeThread(hThread)
    k32.CloseHandle(hThread)
    k32.CloseHandle(hProc)
    return pid

if __name__ == "__main__":
    game_dir = r"E:\CODOL_SANDBOX\RUN001"
    target = os.path.join(game_dir, "codoMP_client_shipRetail.exe")
    bootstrapper = os.path.join(game_dir, "Ayria", "Bootstrapper32.dll")
    pid = launch_and_inject(target, bootstrapper, "-qa", cwd=game_dir)
    print("Launch completed, PID:", pid)
