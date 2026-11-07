import ctypes, ctypes.wintypes as wt, sys
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD),
                ("Alignment1", wt.DWORD),
                ("RegionSize", ctypes.c_ulonglong),
                ("State", wt.DWORD),
                ("Protect", wt.DWORD),
                ("Type", wt.DWORD),
                ("Alignment2", wt.DWORD)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
h = k32.GetCurrentProcess()
print("sizeof MBI", ctypes.sizeof(MBI))
m = MBI()
got = k32.VirtualQueryEx(h, ctypes.c_void_p(0x400000), ctypes.byref(m), ctypes.sizeof(m))
print("got", got, "base 0x%08X" % (m.BaseAddress or 0), "size 0x%X" % m.RegionSize, "state 0x%X" % m.State, "prot 0x%X" % m.Protect)
addr = 0x400000
while addr < 0xE65000:
    got = k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(m), ctypes.sizeof(m))
    if not got: break
    b = m.BaseAddress or 0
    print("  0x%08X  size=0x%-8X state=0x%X prot=0x%02X type=0x%X" % (b, m.RegionSize, m.State, m.Protect, m.Type))
    nxt = b + m.RegionSize
    if nxt <= addr: break
    addr = nxt
