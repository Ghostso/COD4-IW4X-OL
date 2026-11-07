# -*- coding: utf-8 -*-
import ctypes, ctypes.wintypes as wt
import os, sys, time, subprocess, struct

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
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualAllocEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
k32.WriteProcessMemory.restype = wt.BOOL
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.CreateRemoteThread.restype = wt.HANDLE
k32.CreateRemoteThread.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.ResumeThread.restype = wt.DWORD
k32.WaitForSingleObject.restype = wt.DWORD
k32.GetExitCodeThread.restype = wt.BOOL
k32.GetExitCodeThread.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.CloseHandle.restype = wt.BOOL

def rpm(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)):
        return buf.raw[:n.value]
    return b""

def wpm(h, addr, data):
    b = bytes(data)
    buf = (ctypes.c_char * len(b)).from_buffer_copy(b)
    old = wt.DWORD(0)
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(b), 0x40, ctypes.byref(old))
    n = ctypes.c_size_t(0)
    ok = bool(k32.WriteProcessMemory(h, ctypes.c_void_p(addr), buf, len(b), ctypes.byref(n))) and n.value == len(b)
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(b), old.value, ctypes.byref(old))
    return ok

def main():
    game_dir = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
    exe_path = os.path.join(game_dir, "codoMP_client_shipRetail.exe")
    bootstrapper = os.path.join(game_dir, "Ayria", "Bootstrapper32.dll")
    
    os.environ["OLMOD_PROCESS_ROLE"] = "dedicated"
    os.environ["OLMOD_DEDICATED_CONTROL_PORT"] = "28961"
    os.environ["OLMOD_CLIENT_BRIDGE_PORT"] = "28962"
    os.environ["OLMOD_CONSOLE_LOG"] = "1"
    
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    pi = PROCESS_INFORMATION()
    cmdline = f'"{exe_path}" -qa'
    
    CREATE_SUSPENDED = 0x00000004
    ok = k32.CreateProcessW(None, cmdline, None, None, False, CREATE_SUSPENDED, None, game_dir, ctypes.byref(si), ctypes.byref(pi))
    if not ok: return
        
    pid = pi.dwProcessId
    hProc = pi.hProcess
    hThread = pi.hThread
    
    # Patch mutex in memory
    mutex_addr = 0x00400000 + 0x9DBA14
    new_name = b"Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB31}}\x00"
    wpm(hProc, mutex_addr, new_name)
    
    k32.ResumeThread(hThread)
    k32.CloseHandle(hThread)
    
    t0 = time.time()
    while time.time() - t0 < 8.0:
        b = rpm(hProc, 0x0077F6EF, 2)
        if len(b) == 2 and b[0] == 0x75:
            wpm(hProc, 0x0077F6EF, b"\xEB" + b[1:2])
            break
        time.sleep(0.02)
        
    time.sleep(0.8)
    
    # Inject Bootstrapper32.dll
    raw_dll = bootstrapper.encode("utf-16le") + b"\x00\x00"
    pRemote = k32.VirtualAllocEx(hProc, None, len(raw_dll) + 16, 0x3000, 0x04)
    wpm(hProc, pRemote, raw_dll)

    pLoadLibW = 0x76D70000 + 0x21960
    tid = wt.DWORD(0)
    th = k32.CreateRemoteThread(hProc, None, 0, ctypes.c_void_p(pLoadLibW), ctypes.c_void_p(pRemote), 0, ctypes.byref(tid))
    if th:
        k32.WaitForSingleObject(th, 3000)
        hModBoot = wt.DWORD(0)
        k32.GetExitCodeThread(th, ctypes.byref(hModBoot))
        k32.CloseHandle(th)
        print(f"[+] Bootstrapper32.dll injected! HMODULE = 0x{hModBoot.value:08X}")
        
    time.sleep(2)
    
    # Check CodolGameServer.log
    log_file = os.path.join(game_dir, "Ayria", "Logs", "CodolGameServer.log")
    if os.path.exists(log_file):
        print("=== CodolGameServer.log ===")
        print(open(log_file, "r", encoding="utf-8", errors="replace").read().strip())
    else:
        print("[!] CodolGameServer.log not found")

    k32.TerminateProcess(hProc, 0)
    k32.CloseHandle(hProc)

if __name__ == "__main__":
    main()