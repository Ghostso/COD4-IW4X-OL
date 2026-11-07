import ctypes, ctypes.wintypes as wt, struct, sys
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.CloseHandle.restype = wt.BOOL

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]

pid = int(sys.argv[1])
proc = k32.OpenProcess(0x1F0FFF, False, pid)
if not proc:
    print("open failed", ctypes.get_last_error()); sys.exit(1)

for addr in [0x400000, 0x401000, 0x4FEA20, 0x77F6EF, 0xB9A78E]:
    buf = ctypes.create_string_buffer(16)
    n = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(proc, ctypes.c_void_p(addr), buf, 16, ctypes.byref(n))
    mbi = MEMORY_BASIC_INFORMATION()
    k32.VirtualQueryEx(proc, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi))
    data = buf.raw[:n.value] if ok else b""
    print(f"0x{addr:08X}: ok={bool(ok)} read={n.value} protect=0x{mbi.Protect:X} state=0x{mbi.State:X} bytes={data.hex(' ') if data else '(none)'}")

k32.CloseHandle(proc)
