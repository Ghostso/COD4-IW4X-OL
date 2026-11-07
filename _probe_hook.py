import ctypes, ctypes.wintypes as wt, struct, sys
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.CloseHandle.restype = wt.BOOL

pid = int(sys.argv[1])
proc = k32.OpenProcess(0x1F0FFF, False, pid)
if not proc:
    print("open failed", ctypes.get_last_error())
    sys.exit(1)

# Com_Frame RVA = 0xFEA20, base = 0x400000
addr = 0x400000 + 0xFEA20
buf = ctypes.create_string_buffer(16)
n = ctypes.c_size_t(0)
k32.ReadProcessMemory(proc, ctypes.c_void_p(addr), buf, 16, ctypes.byref(n))
data = buf.raw[:n.value]
print(f"Com_Frame @ 0x{addr:08X}: {data.hex(' ')}")
if data and data[0] == 0xE9:
    rel = struct.unpack_from("<i", data, 1)[0]
    target = addr + 5 + rel
    print(f"  -> JMP to 0x{target:08X}")
else:
    print("  -> NOT hooked (no E9)")

k32.CloseHandle(proc)
