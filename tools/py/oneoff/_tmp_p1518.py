import ctypes, ctypes.wintypes as wt, struct, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes=[wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes=[wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
pid = int(sys.argv[1])
out = sys.argv[2]
lines=[]
h = k32.OpenProcess(0x0008|0x0010|0x0020|0x0400, False, pid)
lines.append('handle=%s err=%d' % (h, ctypes.get_last_error()))
def rd(va,n):
    buf=ctypes.create_string_buffer(n); g=ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n, ctypes.byref(g)) and g.value==n:
        return buf.raw
    return None
if h:
    for va,label in ((0x082E1518,'dwRoomMatchUber'),(0x082E1514,'?'),(0x082E13FC,'dwRoomImp')):
        b=rd(va,4)
        lines.append('  [0x%08X] %-16s = %s' % (va,label,('0x%08X'%struct.unpack('<I',b)[0]) if b else 'READ-FAIL err=%d'%ctypes.get_last_error()))
    b=rd(0x00400000,4)
    lines.append('  sanity 0x400000 = %s' % (b.hex() if b else 'FAIL'))
    k32.CloseHandle(h)
open(out,'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))
