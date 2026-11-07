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
    old = wt.DWORD(0)
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), 0x40, ctypes.byref(old))
    n = ctypes.c_size_t(0)
    ok = bool(k32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data), ctypes.byref(n))) and n.value == len(data)
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(old))
    return ok

def main():
    game_dir = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
    exe_path = os.path.join(game_dir, "codoMP_client_shipRetail.exe")
    bootstrapper = os.path.join(game_dir, "Ayria", "Bootstrapper32.dll")
    plugin_path = os.path.join(game_dir, "Ayria", "Plugins", "CodolGameServer.Localnet32")
    
    # Clean previous logs
    log_dir = os.path.join(game_dir, "Ayria", "Logs")
    for lf in ["CodolGameServer.log", "Bootstrapper32.log", "Localnetworking.log"]:
        lp = os.path.join(log_dir, lf)
        if os.path.exists(lp):
            try: os.remove(lp)
            except: pass
            
    os.environ["OLMOD_PROCESS_ROLE"] = "dedicated"
    os.environ["OLMOD_DEDICATED_CONTROL_PORT"] = "28961"
    os.environ["OLMOD_CLIENT_BRIDGE_PORT"] = "28962"
    os.environ["OLMOD_CONSOLE_LOG"] = "1"
    
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
    
    # Patch mutex in memory
    mutex_addr = 0x00400000 + 0x9DBA14
    new_name = b"Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB31}}\x00"
    wpm(hProc, mutex_addr, new_name)
    print("[+] Patched mutex in memory to ...31}}")
    
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
        
    if not unlocked:
        print("[!] Unpack gate not reached.")
        k32.TerminateProcess(hProc, 0)
        k32.CloseHandle(hProc)
        return

    time.sleep(0.8)
    
    # Inject Bootstrapper32.dll
    print("[*] Injecting Bootstrapper32.dll...")
    raw_dll = bootstrapper.encode("utf-16le") + b"\x00\x00"
    pRemote = k32.VirtualAllocEx(hProc, None, len(raw_dll) + 16, 0x3000, 0x04)
    wpm(hProc, pRemote, raw_dll)

    pLoadLibW = 0x76D70000 + 0x21960
    tid = wt.DWORD(0)
    th = k32.CreateRemoteThread(hProc, None, 0, ctypes.c_void_p(pLoadLibW), ctypes.c_void_p(pRemote), 0, ctypes.byref(tid))
    if th:
        k32.WaitForSingleObject(th, 3000)
        k32.CloseHandle(th)
        print("[+] Bootstrapper32 injected!")
        
    # Wait for frame hook installed log
    print("[*] Waiting for engine binding and frame hook...")
    log_file = os.path.join(log_dir, "CodolGameServer.log")
    t1 = time.time()
    hooked = False
    while time.time() - t1 < 8.0:
        if os.path.exists(log_file):
            content = open(log_file, "r", encoding="utf-8", errors="replace").read()
            if "frame hook installed" in content:
                print(f"[+] Verified in log: frame hook installed at t={time.time() - t1:.2f}s!")
                hooked = True
                break
        time.sleep(0.1)
        
    if not hooked:
        print("[!] Frame hook not detected in log.")

    # Now load CodolGameServer.Localnet32 explicitly via LoadLibraryW so we have its exact HMODULE!
    print("[*] Resolving CodolGameServer.Localnet32 module handle in process...")
    raw_plugin = plugin_path.encode("utf-16le") + b"\x00\x00"
    pPluginRemote = k32.VirtualAllocEx(hProc, None, len(raw_plugin) + 16, 0x3000, 0x04)
    wpm(hProc, pPluginRemote, raw_plugin)
    
    th_plug = k32.CreateRemoteThread(hProc, None, 0, ctypes.c_void_p(pLoadLibW), ctypes.c_void_p(pPluginRemote), 0, ctypes.byref(tid))
    hModPlugin = wt.DWORD(0)
    if th_plug:
        k32.WaitForSingleObject(th_plug, 3000)
        k32.GetExitCodeThread(th_plug, ctypes.byref(hModPlugin))
        k32.CloseHandle(th_plug)
        print(f"[+] CodolGameServer.Localnet32 HMODULE = 0x{hModPlugin.value:08X}")
        
    if hModPlugin.value != 0:
        # RVA of CODOL_GameServerSetEnabled is 0x1F57F0
        pSetEnabled = hModPlugin.value + 0x1F57F0
        print(f"[*] Calling CODOL_GameServerSetEnabled(true) @ 0x{pSetEnabled:08X}...")
        th_enable = k32.CreateRemoteThread(hProc, None, 0, ctypes.c_void_p(pSetEnabled), ctypes.c_void_p(1), 0, ctypes.byref(tid))
        if th_enable:
            k32.WaitForSingleObject(th_enable, 3000)
            ret_val = wt.DWORD(0)
            k32.GetExitCodeThread(th_enable, ctypes.byref(ret_val))
            k32.CloseHandle(th_enable)
            print(f"[+] CODOL_GameServerSetEnabled(true) returned: {ret_val.value}")
            
    time.sleep(2)
    # Check sockets
    net = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
    print(f"\n--- Sockets for PID {pid} ---")
    found_28960 = False
    for line in net.stdout.splitlines():
        if str(pid) in line or ":28960" in line:
            print(" ", line.strip())
            if ":28960" in line:
                found_28960 = True
                
    if found_28960:
        print("\n[★★★ SUCCESS ★★★] Native Dedicated Server UDP 28960 IS LISTENING!")
    else:
        print("\n[-] 28960 not listening yet.")
        
    k32.TerminateProcess(hProc, 0)
    k32.CloseHandle(hProc)
    print("[*] Probe ended, cleaned up.")

if __name__ == "__main__":
    main()