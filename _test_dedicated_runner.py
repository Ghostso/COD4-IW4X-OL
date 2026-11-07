import ctypes, ctypes.wintypes as wt
import os, sys, time, struct, subprocess

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
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.CreateRemoteThread.restype = wt.HANDLE
k32.CreateRemoteThread.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.ResumeThread.restype = wt.DWORD
k32.ResumeThread.argtypes = [wt.HANDLE]
k32.WaitForSingleObject.restype = wt.DWORD
k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
k32.CloseHandle.restype = wt.BOOL
k32.CloseHandle.argtypes = [wt.HANDLE]

def rpm(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)):
        return buf.raw[:n.value]
    return b""

def wpm(h, addr, data):
    n = ctypes.c_size_t(0)
    return bool(k32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data), ctypes.byref(n))) and n.value == len(data)

def start_native_dedicated(game_dir):
    exe_path = os.path.join(game_dir, "codoMP_client_shipRetail.exe")
    bootstrapper = os.path.join(game_dir, "Ayria", "Bootstrapper32.dll")
    
    env = os.environ.copy()
    env["OLMOD_PROCESS_ROLE"] = "dedicated"
    env["OLMOD_DEDICATED_CONTROL_PORT"] = "28961"
    env["OLMOD_CLIENT_BRIDGE_PORT"] = "28962"
    env["OLMOD_ROOM_OWNER_PORT"] = "28970"
    env["OLMOD_CONSOLE_LOG"] = "1"
    env["OLMOD_CLAIM_LOBBY"] = "1"
    
    # 1. Start room owner on 28970 if needed
    ro_exe = os.path.join(game_dir, "Ayria", "ol_room_owner.exe")
    if os.path.isfile(ro_exe):
        subprocess.Popen([ro_exe], cwd=game_dir, creationflags=0x08000000)
    
    # 2. Launch codoMP suspended
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    pi = PROCESS_INFORMATION()
    cmdline = f'"{exe_path}" -qa'
    
    CREATE_SUSPENDED = 0x00000004
    ok = k32.CreateProcessW(None, cmdline, None, None, False, CREATE_SUSPENDED, None, game_dir, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print(f"CreateProcessW failed: {ctypes.get_last_error()}")
        return None
    
    pid = pi.dwProcessId
    hProc = pi.hProcess
    hThread = pi.hThread
    print(f"Created dedicated server process suspended (PID={pid})")
    
    # 3. Patch mutex name before resume so no collision with client
    mutex_addr = 0x00400000 + 0x9DBA14
    wpm(hProc, mutex_addr, b"Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB31}}\x00")
    print("Patched dedicated mutex name in memory to ...31}}")
    
    # 4. Inject Bootstrapper32.dll
    raw_dll = bootstrapper.encode("utf-16le") + b"\x00\x00"
    pRemote = k32.VirtualAllocEx(hProc, None, len(raw_dll) + 16, 0x3000, 0x04)
    wpm(hProc, pRemote, raw_dll)
    
    # 32-bit SysWOW64 LoadLibraryW is at 0x76D70000 + 0x21960 = 0x76D91960
    pLoadLibW = 0x76D70000 + 0x21960
    tid = wt.DWORD(0)
    th = k32.CreateRemoteThread(hProc, None, 0, ctypes.c_void_p(pLoadLibW), ctypes.c_void_p(pRemote), 0, ctypes.byref(tid))
    if th:
        k32.WaitForSingleObject(th, 3000)
        k32.CloseHandle(th)
        print(f"Injected Bootstrapper32.dll (tid={tid.value})")
    
    # 5. Resume main thread
    k32.ResumeThread(hThread)
    k32.CloseHandle(hThread)
    print("Resumed dedicated server main thread!")
    
    # 6. Watch 0x0077F6EF and apply 75->EB unpack patch
    JNE_ADDR = 0x0077F6EF
    t0 = time.time()
    unlocked = False
    print("Monitoring TP3 unpack gate (0x0077F6EF)...")
    while time.time() - t0 < 10.0:
        b = rpm(hProc, JNE_ADDR, 2)
        if len(b) == 2 and b[0] == 0x75:
            wpm(hProc, JNE_ADDR, b"\xEB" + b[1:2])
            print(f"  [+] Unpack patch 75->EB applied at t={time.time() - t0:.2f}s!")
            unlocked = True
            break
        time.sleep(0.1)
    
    k32.CloseHandle(hProc)
    return pid

if __name__ == "__main__":
    game_dir = r"E:\CODOL_SANDBOX\RUN001"
    pid = start_native_dedicated(game_dir)
    print(f"Dedicated server runner completed, PID={pid}")
    
    time.sleep(6)
    # Check listening ports
    net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
    print("\n--- Active listening sockets ---")
    for line in net.stdout.splitlines():
        if any(port in line for port in [":28960", ":28961", ":28970"]):
            print(" ", line.strip())
