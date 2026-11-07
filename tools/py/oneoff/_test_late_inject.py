import ctypes, ctypes.wintypes as wt
import os, sys, subprocess

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualAllocEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
k32.WriteProcessMemory.restype = wt.BOOL
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.CreateRemoteThread.restype = wt.HANDLE
k32.CreateRemoteThread.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.WaitForSingleObject.restype = wt.DWORD
k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
k32.GetExitCodeThread.restype = wt.BOOL
k32.GetExitCodeThread.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.CloseHandle.restype = wt.BOOL
k32.CloseHandle.argtypes = [wt.HANDLE]

res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq codoMP_client_shipRetail.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True)
pids = [int(r.split(',')[1].strip('"')) for r in res.stdout.strip().splitlines() if 'codoMP' in r]
print("Running codoMP PIDs:", pids)
if not pids:
    print("No codoMP running")
    sys.exit(0)

pid = pids[0]
h = k32.OpenProcess(0x0008 | 0x0010 | 0x0020 | 0x0400, False, pid)
if not h:
    print(f"OpenProcess failed: {ctypes.get_last_error()}")
    sys.exit(1)

dll_path = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32"
# Use UTF-16LE for wide-string API LoadLibraryW
raw = dll_path.encode("utf-16le") + b"\x00\x00"

p_str = k32.VirtualAllocEx(h, None, len(raw) + 16, 0x3000, 0x40)
print(f"Allocated remote wide string @ 0x{p_str:X}")

n = ctypes.c_size_t(0)
k32.WriteProcessMemory(h, ctypes.c_void_p(p_str), raw, len(raw), ctypes.byref(n))

k32_mod = k32.GetModuleHandleW("kernel32.dll")
p_load = k32.GetProcAddress(k32_mod, b"LoadLibraryW")
print(f"LoadLibraryW @ 0x{p_load:X}")

tid = wt.DWORD(0)
th = k32.CreateRemoteThread(h, None, 0, ctypes.c_void_p(p_load), ctypes.c_void_p(p_str), 0, ctypes.byref(tid))
if th:
    print(f"CreateRemoteThread SUCCESS! Thread ID = {tid.value}")
    k32.WaitForSingleObject(th, 5000)
    exit_code = wt.DWORD(0)
    k32.GetExitCodeThread(th, ctypes.byref(exit_code))
    print(f"Thread exit code (HMODULE of DLL): 0x{exit_code.value:X}")
    k32.CloseHandle(th)
else:
    print(f"CreateRemoteThread FAILED: {ctypes.get_last_error()}")

k32.CloseHandle(h)
