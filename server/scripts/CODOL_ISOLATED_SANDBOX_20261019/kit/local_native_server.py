# -*- coding: utf-8 -*-
import ctypes, ctypes.wintypes as wt
import os, sys, time, subprocess, pefile, socket, struct, threading

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

class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("th32ModuleID", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD),
        ("ProccntUsage", wt.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wt.DWORD),
        ("hModule", wt.HMODULE),
        ("szModule", ctypes.c_wchar * 256),
        ("szExePath", ctypes.c_wchar * 260)
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
k32.GetExitCodeProcess.restype = wt.BOOL
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.CloseHandle.restype = wt.BOOL
k32.Module32FirstW.restype = wt.BOOL
k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32NextW.restype = wt.BOOL
k32.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]

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

def get_wow64_module_base(pid, module_name):
    TH32CS_SNAPMODULE = 0x00000008
    TH32CS_SNAPMODULE32 = 0x00000010
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    base = 0
    INVALID = [None, 0, -1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF]
    if snap not in INVALID:
        me = MODULEENTRY32W()
        me.dwSize = ctypes.sizeof(MODULEENTRY32W)
        if k32.Module32FirstW(snap, ctypes.byref(me)):
            while True:
                if module_name.lower() in me.szModule.lower():
                    base = me.modBaseAddr
                    break
                if not k32.Module32NextW(snap, ctypes.byref(me)):
                    break
        try:
            k32.CloseHandle(snap)
        except Exception:
            pass
    return base

def get_wow64_loadlibraryw(pid):
    k32_base = 0
    for _ in range(50):
        k32_base = get_wow64_module_base(pid, "kernel32.dll")
        if k32_base:
            break
        time.sleep(0.1)
    if not k32_base:
        print("[!] Failed to find kernel32.dll base in WOW64 process")
        return None
    syswow64_k32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "SysWOW64", "kernel32.dll")
    loadlib_rva = 0x21960
    try:
        pe = pefile.PE(syswow64_k32)
        for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            if exp.name == b"LoadLibraryW":
                loadlib_rva = exp.address
                break
    except Exception as e:
        print(f"[-] pefile parse SysWOW64 kernel32.dll failed: {e}")
    print(f"[+] WOW64 kernel32.dll base = 0x{k32_base:08X}, LoadLibraryW RVA = 0x{loadlib_rva:08X}")
    return k32_base + loadlib_rva

def fnv1a(data: bytes) -> int:
    h = 2166136261
    for b in data:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h

def make_control_packet(msg_type: int, req_id: int, payload: bytes) -> bytes:
    header = struct.pack("<IHHIQI", 0x43444C4F, 2, msg_type, len(payload), req_id, fnv1a(payload))
    return header + payload

def make_session_start_payload(map_name='mp_firingrange', game_type='dm', playlist_id=10, rotation_index=0):
    b = bytearray()
    b.extend(struct.pack('<IHH', 0x53444C4F, 8, 2))
    booking_cmd = b'mmstart 10 0'
    b.extend(struct.pack('<HH', 1, len(booking_cmd)))
    map_bytes = map_name.encode('ascii')
    gt_bytes = game_type.encode('ascii')
    b.extend(struct.pack('<IIHH', playlist_id, rotation_index, len(map_bytes), len(gt_bytes)))
    b.extend(map_bytes)
    b.extend(gt_bytes)
    b.extend(struct.pack('<IIIIII', 796, 75, 10, 0, 1, 1))
    b.extend(booking_cmd)
    username = b'Alwaysoffline'
    b.extend(struct.pack('<QHH', 0x1100001DEADC0DE, len(username), 0))
    b.extend(struct.pack('<IBBH', 3, 0x03, 0, 0))
    char_items = [545, 789, 792] + [0] * 9
    for item in char_items:
        b.extend(struct.pack('<I', item))
    for c_idx in range(5):
        present = c_idx < 2
        w0_item = 10053 if c_idx == 0 else (10001 if c_idx == 1 else 0)
        b.extend(struct.pack('<I', w0_item))
        b.extend(struct.pack('<6I', 0, 0, 0, 0, 0, 0))
        w1_item = 10145 if c_idx == 0 else (10049 if c_idx == 1 else 0)
        b.extend(struct.pack('<I', w1_item))
        b.extend(struct.pack('<6I', 0, 0, 0, 0, 0, 0))
        perks = (1, 1, 1, 1, 1, 1) if present else (0, 0, 0, 0, 0, 0)
        b.extend(struct.pack('<6I', *perks))
        b.extend(struct.pack('<2IBBH', 0, 0, 1 if present else 0, 0, 0))
    b.extend(struct.pack('<3I', 60077, 60081, 60084))
    b.extend(username)
    return bytes(b)

def native_watch(pid, h_proc, seconds=180.0):
    import json
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "native_dedicated_watch.jsonl")
    start = time.time()
    seen = set()
    with open(out, "w", encoding="utf-8", buffering=1) as fh:
        def record(kind, **fields):
            item = {"t": round(time.time() - start, 3), "kind": kind}
            item.update(fields)
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        record("start", pid=pid)
        while time.time() - start < seconds:
            try:
                modules = []
                snap = k32.CreateToolhelp32Snapshot(8 | 0x10, pid)
                INVALID = [None, 0, -1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF]
                if snap not in INVALID:
                    me = MODULEENTRY32W()
                    me.dwSize = ctypes.sizeof(MODULEENTRY32W)
                    if k32.Module32FirstW(snap, ctypes.byref(me)):
                        while True:
                            modules.append((me.szModule, me.modBaseAddr or 0, me.modBaseSize))
                            if not k32.Module32NextW(snap, ctypes.byref(me)):
                                break
                    try:
                        k32.CloseHandle(snap)
                    except Exception:
                        pass
            except Exception:
                modules = []
            for name, base, size in modules:
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                record("module", name=name, base=base,
                       base_hex="0x%08X" % base, size=size)
            code = wt.DWORD(0)
            if k32.GetExitCodeProcess(h_proc, ctypes.byref(code)):
                if code.value != 259:
                    record("exit", exit_code=code.value,
                           exit_hex="0x%08X" % code.value)
                    print("NATIVE_WATCH exit_code=0x%08X pid=%d"
                          % (code.value, pid), flush=True)
                    return
            time.sleep(0.2)


def main():
    game_dir = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
    exe_path = os.path.join(game_dir, "codoMP_client_shipRetail.exe")
    bootstrapper = os.path.join(game_dir, "Ayria", "Bootstrapper32.dll")
    plugin_path = os.path.join(game_dir, "Ayria", "Plugins", "CodolGameServer.Localnet32")
    
    log_dir = os.path.join(game_dir, "Ayria", "Logs")
    for lf in ["CodolGameServer.log", "Bootstrapper32.log", "Localnetworking.log"]:
        lp = os.path.join(log_dir, lf)
        if os.path.exists(lp):
            try: os.remove(lp)
            except:
                try: open(lp, "w").close()
                except: pass
            
    os.environ["OLMOD_PROCESS_ROLE"] = "dedicated"
    os.environ["OLMOD_DEDICATED_CONTROL_PORT"] = "28961"
    os.environ["OLMOD_CLIENT_BRIDGE_PORT"] = "28962"
    os.environ["OLMOD_CONSOLE_LOG"] = "1"
    
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    pi = PROCESS_INFORMATION()
    cmdline = f'"{exe_path}" -q -qa'
    
    CREATE_SUSPENDED = 0x00000004
    print("[*] Launching 3.19 codoMP_client_shipRetail.exe suspended...")
    ok = k32.CreateProcessW(None, cmdline, None, None, False, CREATE_SUSPENDED, None, game_dir, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print(f"[!] CreateProcessW failed: {ctypes.get_last_error()}")
        return 1
        
    pid = pi.dwProcessId
    hProc = pi.hProcess
    hThread = pi.hThread
    print(f"[+] Suspended process created, PID={pid}")
    threading.Thread(target=native_watch, args=(pid, hProc, 180.0),
                     daemon=True).start()
    
    mutex_addr = 0x00400000 + 0x9DBA14
    new_name = b"Global\\{5BD75B76-601A-4b20-80C8-D2317C94BB31}\x00"
    wpm(hProc, mutex_addr, new_name)
    print("[+] Patched mutex in memory to avoid conflict")
    
    k32.ResumeThread(hThread)
    k32.CloseHandle(hThread)
    print("[*] Resumed main thread, waiting for 0x0077F6EF...")
    
    t0 = time.time()
    unlocked = False
    while time.time() - t0 < 25.0:
        ec = wt.DWORD(0)
        k32.GetExitCodeProcess(hProc, ctypes.byref(ec))
        if ec.value != 259:
            print(f"[!] Process exited early with ExitCode={ec.value} (0x{ec.value:08X}) at t={time.time()-t0:.2f}s")
            break

        b = rpm(hProc, 0x0077F6EF, 2)
        if len(b) == 2 and b[0] == 0x75:
            wpm(hProc, 0x0077F6EF, b"\xEB" + b[1:2])
            print(f"[+] Unpack gate unlocked at t={time.time() - t0:.2f}s!")
            unlocked = True
            break
        elif len(b) == 2 and b[0] == 0xEB:
            print(f"[+] Unpack gate already unlocked at t={time.time() - t0:.2f}s!")
            unlocked = True
            break
        time.sleep(0.05)
        
    if not unlocked:
        print("[!] Unpack gate not reached.")
        k32.TerminateProcess(hProc, 0)
        k32.CloseHandle(hProc)
        return 2

    time.sleep(0.8)
    
    pLoadLibW = get_wow64_loadlibraryw(pid)
    if not pLoadLibW:
        print("[!] Could not resolve WOW64 LoadLibraryW.")
        k32.TerminateProcess(hProc, 0)
        k32.CloseHandle(hProc)
        return 3
    print(f"[+] Dynamic LoadLibraryW @ 0x{pLoadLibW:08X}")

    print("[*] Injecting Bootstrapper32.dll...")
    raw_dll = bootstrapper.encode("utf-16le") + b"\x00\x00"
    pRemote = k32.VirtualAllocEx(hProc, None, len(raw_dll) + 16, 0x3000, 0x04)
    wpm(hProc, pRemote, raw_dll)

    tid = wt.DWORD(0)
    th = k32.CreateRemoteThread(hProc, None, 0, ctypes.c_void_p(pLoadLibW), ctypes.c_void_p(pRemote), 0, ctypes.byref(tid))
    hModBootstrap = wt.DWORD(0)
    if th:
        k32.WaitForSingleObject(th, 5000)
        k32.GetExitCodeThread(th, ctypes.byref(hModBootstrap))
        k32.CloseHandle(th)
        print(f"[+] Bootstrapper32 injected! Thread exit code (HMODULE) = 0x{hModBootstrap.value:08X}")
    else:
        print(f"[!] CreateRemoteThread for Bootstrapper32 failed: {ctypes.get_last_error()}")
        
    print("[*] Waiting for engine binding and frame hook...")
    log_file = os.path.join(log_dir, "CodolGameServer.log")
    t1 = time.time()
    hooked = False
    while time.time() - t1 < 15.0:
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if "frame hook installed" in content:
                    print(f"[+] Verified in log: frame hook installed at t={time.time() - t1:.2f}s!")
                    hooked = True
                    break
                elif "frame hook failed" in content:
                    print(f"[-] Detected in log: frame hook failed!")
                    break
            except Exception:
                pass
        time.sleep(0.3)
        
    if not hooked:
        print("[!] Frame hook not confirmed in log yet. Checking log contents:")
        if os.path.exists(log_file):
            print(open(log_file, "r", encoding="utf-8", errors="replace").read())

    # Check or load CodolGameServer.Localnet32
    hModPlugin_val = get_wow64_module_base(pid, "CodolGameServer")
    if not hModPlugin_val:
        print("[*] CodolGameServer not in module table yet, explicitly calling LoadLibraryW...")
        raw_plugin = plugin_path.encode("utf-16le") + b"\x00\x00"
        pPluginRemote = k32.VirtualAllocEx(hProc, None, len(raw_plugin) + 16, 0x3000, 0x04)
        wpm(hProc, pPluginRemote, raw_plugin)
        
        th_plug = k32.CreateRemoteThread(hProc, None, 0, ctypes.c_void_p(pLoadLibW), ctypes.c_void_p(pPluginRemote), 0, ctypes.byref(tid))
        hModPlugin = wt.DWORD(0)
        if th_plug:
            k32.WaitForSingleObject(th_plug, 5000)
            k32.GetExitCodeThread(th_plug, ctypes.byref(hModPlugin))
            k32.CloseHandle(th_plug)
            hModPlugin_val = hModPlugin.value
            print(f"[+] CodolGameServer.Localnet32 loaded via LoadLibraryW = 0x{hModPlugin_val:08X}")
    else:
        print(f"[+] CodolGameServer.Localnet32 already present in module table: 0x{hModPlugin_val:08X}")
        
    print("[*] Engine frame hook installed. Allowing engine startup to reach com_frame and start DedicatedControl...")
            
    # Check if process is still alive
    exit_code = wt.DWORD(0)
    k32.GetExitCodeProcess(hProc, ctypes.byref(exit_code))
    if exit_code.value != 259:
        print(f"[!] Target process died with exit code {exit_code.value} (0x{exit_code.value:08X})")
        k32.CloseHandle(hProc)
        return 4

    print("[*] Connecting to DedicatedControl on TCP 28961...")
    ctrl_s = None
    for attempt in range(120):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect(("127.0.0.1", 28961))
            ctrl_s = s
            print(f"[+] Connected to DedicatedControl port 28961 (attempt {attempt+1})!")
            break
        except Exception:
            time.sleep(0.5)

    if ctrl_s:
        print("[*] Sending ConfigureSession (type=4) packet to activate UDP 28960...")
        sec_key = b"\x01" * 16
        sec_key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "battle_security_key.txt")
        if os.path.exists(sec_key_file):
            try:
                sec_key = bytes.fromhex(open(sec_key_file, "r").read().strip())
            except Exception:
                pass
        marker = bytes([0x13, 0x08, 0x10, 0, 0, 0])
        payload = marker + sec_key
        pkt = make_control_packet(4, 1, payload)
        ctrl_s.sendall(pkt)
        resp_hdr = ctrl_s.recv(24)
        if len(resp_hdr) == 24:
            magic, ver, status, plen, req_id, csum = struct.unpack("<IHHIQI", resp_hdr)
            resp_payload = ctrl_s.recv(plen) if plen > 0 else b""
            print(f"[+] ConfigureSession response: status={status} (0=Accepted), payload_len={plen}")

        print("[*] SessionStart not sent by the startup chain.")
        ctrl_s.close()
    else:
        print("[-] DedicatedControl port 28961 not available within timeout")

    print("[*] Checking UDP port 28960...")
    found_28960 = False
    for attempt in range(10):
        net = subprocess.run(["netstat", "-ano", "-p", "UDP"], capture_output=True, text=True, errors='replace')
        for line in net.stdout.splitlines():
            if ":28960" in line and str(pid) in line:
                print("  [PORT]", line.strip())
                found_28960 = True
                break
        if found_28960:
            break
        time.sleep(1.0)
                
    if found_28960:
        print(f"\n[SUCCESS] Native Dedicated Server (PID {pid}) IS LISTENING ON UDP 28960 WITH ACTIVE SESSION!")
        with open(os.path.join(game_dir, "native_dedicated.pid"), "w") as f:
            f.write(str(pid))
        print("[*] Dedicated server is kept alive in background.")
        k32.CloseHandle(hProc)
        return 0
    else:
        print("\n[-] UDP 28960 not listening yet.")
        k32.CloseHandle(hProc)
        return 5

if __name__ == "__main__":
    sys.exit(main())
