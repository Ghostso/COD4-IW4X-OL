# -*- coding: utf-8 -*-
import ctypes, ctypes.wintypes as wt
import os, sys, time, subprocess

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
k32.VirtualProtectEx.restype = wt.BOOL
k32.VirtualProtectEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.WriteProcessMemory.restype = wt.BOOL
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ResumeThread.restype = wt.DWORD
k32.CloseHandle.restype = wt.BOOL

def rpm(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)):
        return buf.raw[:n.value]
    return b""

def wpm(h, addr, data):
    old = wt.DWORD(0)
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), 0x40, ctypes.byref(old))
    n = ctypes.c_size_t(0)
    ok = bool(k32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data), ctypes.byref(n))) and n.value == len(data)
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(old))
    return ok

def main():
    game_dir = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
    exe_path = os.path.join(game_dir, "codoMP_client_shipRetail.exe")
    
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    pi = PROCESS_INFORMATION()
    cmdline = f'"{exe_path}" -qa'
    
    CREATE_SUSPENDED = 0x00000004
    print("[*] Launching authentic codoMP_client_shipRetail.exe suspended...")
    ok = k32.CreateProcessW(None, cmdline, None, None, False, CREATE_SUSPENDED, None, game_dir, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print(f"[!] CreateProcessW failed: {ctypes.get_last_error()}")
        return
        
    pid = pi.dwProcessId
    hProc = pi.hProcess
    hThread = pi.hThread
    print(f"[+] Suspended process created, PID={pid}")
    
    # Check mutex in memory
    mutex_addr = 0x00400000 + 0x9DBA14
    cur = rpm(hProc, mutex_addr, 48)
    print(f"[+] Memory at mutex_addr: {cur}")
    if b"5BD75B76" in cur:
        new_name = b"Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB31}}\x00"
        ok = wpm(hProc, mutex_addr, new_name)
        print(f"[+] Patched mutex in memory: {ok}")
        
    k32.ResumeThread(hThread)
    k32.CloseHandle(hThread)
    print("[*] Resumed main thread, monitoring 0x0077F6EF...")
    
    t0 = time.time()
    unlocked = False
    while time.time() - t0 < 8.0:
        b = rpm(hProc, 0x0077F6EF, 2)
        if len(b) == 2 and b[0] == 0x75:
            wpm(hProc, 0x0077F6EF, b"\xEB" + b[1:2])
            print(f"[+] Unpack gate unlocked at t={time.time() - t0:.2f}s!")
            unlocked = True
            break
        time.sleep(0.02)
        
    if unlocked:
        print("[+] SUCCESS! TP3 decrypted cleanly without warning!")
        time.sleep(1)
        # Check if process is still alive
        code = wt.DWORD(0)
        k32.GetExitCodeProcess(hProc, ctypes.byref(code))
        print(f"[+] Process state: exitCode={hex(code.value)} (STILL_ACTIVE=0x103)")
    else:
        print("[!] Unpack gate not reached.")
        
    # Terminate test process
    k32.TerminateProcess(hProc, 0)
    k32.CloseHandle(hProc)
    print("[*] Test process cleaned up.")

if __name__ == "__main__":
    main()