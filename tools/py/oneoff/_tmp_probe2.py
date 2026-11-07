
import ctypes, ctypes.wintypes as wt, struct, sys, time
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes=[wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes=[wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
pid = int(sys.argv[1])
for access,label in ((0x0410,'0x0410'), (0x0008|0x0010|0x0020|0x0400,'PROC_ALL')):
    h = k32.OpenProcess(access, False, pid)
    e = ctypes.get_last_error()
    print('%s -> handle=%s err=%d' % (label, h, e))
    if h:
        for va in (0x00400000, 0x082E13FC, 0x0849B61C):
            buf=ctypes.create_string_buffer(4); g=ctypes.c_size_t(0)
            ok=k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, 4, ctypes.byref(g))
            print('    0x%08X ok=%s %s err=%d' % (va, ok, buf.raw.hex(), ctypes.get_last_error()))
        k32.CloseHandle(h)
