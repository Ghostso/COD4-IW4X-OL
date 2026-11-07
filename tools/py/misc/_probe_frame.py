import ctypes, ctypes.wintypes as wt, os, struct, subprocess, sys, time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.CreateRemoteThread.restype = wt.HANDLE
k32.CreateRemoteThread.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.WaitForSingleObject.restype = wt.DWORD
k32.GetExitCodeThread.restype = wt.BOOL
k32.GetExitCodeThread.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.CloseHandle.restype = wt.BOOL

class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE), ("szModule", ctypes.c_wchar * 256),
                ("szExePath", ctypes.c_wchar * 260)]

def module_base(pid, wanted):
    snap = k32.CreateToolhelp32Snapshot(0x08 | 0x10, pid)
    if not snap or snap in (-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF): return 0
    me = MODULEENTRY32W(); me.dwSize = ctypes.sizeof(me)
    base = 0
    if k32.Module32FirstW(snap, ctypes.byref(me)):
        while True:
            if wanted.casefold() in me.szModule.casefold(): base = int(me.modBaseAddr or 0); break
            if not k32.Module32NextW(snap, ctypes.byref(me)): break
    k32.CloseHandle(snap)
    return base

def rpm(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)):
        return buf.raw[:n.value]
    return b""

pid = int(sys.argv[1])
proc = k32.OpenProcess(0x1F0FFF, False, pid)
if not proc:
    print("open failed", ctypes.get_last_error())
    sys.exit(1)

plugin = module_base(pid, "CodolGameServer")
print("plugin base:", hex(plugin))

# CODOL_GameServerGetStatus(enabled*, frameNumber*, serverTime*) -> bool
# export RVA fallback: find it from PE
import pefile
pe = pefile.PE(r"run_codol_001\sandbox_repro_test_20261019\Ayria\Plugins\CodolGameServer.Localnet32")
rva = None
for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
    if exp.name == b"CODOL_GameServerGetStatus":
        rva = exp.address
        break
print("GetStatus RVA:", hex(rva) if rva else None)

addr = plugin + rva
print("GetStatus addr:", hex(addr))

# allocate remote buffers
buf = k32.VirtualAllocEx(proc, None, 12, 0x3000, 4)
print("remote buf:", hex(buf))

for i in range(5):
    tid = wt.DWORD()
    th = k32.CreateRemoteThread(proc, None, 0, ctypes.c_void_p(addr), ctypes.c_void_p(buf), 0, ctypes.byref(tid))
    if not th:
        print("thread failed", ctypes.get_last_error())
        break
    k32.WaitForSingleObject(th, 5000)
    ret = wt.DWORD()
    k32.GetExitCodeThread(th, ctypes.byref(ret))
    k32.CloseHandle(th)
    data = rpm(proc, buf, 12)
    if len(data) == 12:
        enabled, frame, stime = struct.unpack("<III", data)
        print(f"sample {i}: ret={ret.value} enabled={enabled} frame={frame} serverTime={stime}")
    else:
        print(f"sample {i}: ret={ret.value} read failed")
    time.sleep(1)

k32.CloseHandle(proc)
